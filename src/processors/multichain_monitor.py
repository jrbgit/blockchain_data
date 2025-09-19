"""
Multi-Chain Real-time Monitor

Enhanced monitoring dashboard for multiple blockchain networks with chain selection,
cross-chain comparisons, and unified metrics visualization.
"""

import asyncio
import logging
import time
import json
from typing import Optional, Dict, Any, Set, List
from datetime import datetime, timezone, timedelta
from dataclasses import asdict
from collections import defaultdict, deque

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..core.config import Config
from ..core.multichain_client import MultiChainClient
from ..core.multichain_influxdb_client import MultiChainInfluxDB

# Optional analytics import
try:
    from ..analytics.chain_analytics import MultiChainAnalyticsOrchestrator, CrossChainMetrics
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Analytics module not available: {e}")
    MultiChainAnalyticsOrchestrator = None
    CrossChainMetrics = None
    ANALYTICS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MultiChainMonitor:
    """Enhanced multi-chain real-time monitor"""
    
    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        
        # Clients
        self.multichain_client: Optional[MultiChainClient] = None
        self.db_client: Optional[MultiChainInfluxDB] = None
        self.analytics: Optional[MultiChainAnalyticsOrchestrator] = None
        
        # Monitoring configuration
        try:
            self.poll_interval = config.get('monitoring.poll_interval', 3)
        except (AttributeError, KeyError):
            # Fallback if monitoring config doesn't exist
            self.poll_interval = getattr(config, 'poll_interval', 3)
            if hasattr(config, 'monitoring') and isinstance(config.monitoring, dict):
                self.poll_interval = config.monitoring.get('poll_interval', self.poll_interval)
        self.selected_chains: Set[str] = set()
        self.display_mode = "overview"  # overview, detailed, analytics, comparison
        
        # State tracking per chain
        self.chain_states: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.start_time = None
        self.total_blocks_processed = 0
        self.total_transactions_processed = 0
        self.total_errors = 0
        
        # Performance tracking
        self.performance_history = defaultdict(lambda: deque(maxlen=100))
        self.analytics_cache = {}
        self.last_analytics_update = 0
        
        # Control flags
        self.running = False
        self.paused = False
        
        logger.info("Multi-chain monitor initialized")
    
    async def initialize(self) -> bool:
        """Initialize connections and determine starting points"""
        
        logger.info("Initializing multi-chain monitor...")
        
        try:
            # Connect to multi-chain client
            self.multichain_client = MultiChainClient(self.config)
            await self.multichain_client.connect()
            
            # Connect to database
            self.db_client = MultiChainInfluxDB(self.config)
            await self.db_client.connect()
            
            # Initialize analytics (if available)
            if ANALYTICS_AVAILABLE and MultiChainAnalyticsOrchestrator:
                self.analytics = MultiChainAnalyticsOrchestrator(self.config)
                await self.analytics.initialize()
            else:
                self.analytics = None
                logger.info("Analytics module not available, continuing without analytics")
            
            # Get connected chains
            connected_chains = self.multichain_client.get_connected_chains()
            
            # Initialize chain states
            for chain_id in connected_chains:
                await self._initialize_chain_state(chain_id)
            
            # Default to monitoring all connected chains
            self.selected_chains = set(connected_chains)
            
            logger.info(f"Multi-chain monitor initialized for {len(connected_chains)} chains")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize multi-chain monitor: {e}")
            return False
    
    async def _initialize_chain_state(self, chain_id: str):
        """Initialize state tracking for a chain"""
        
        try:
            chain_config = self.multichain_client.get_chain_config(chain_id)
            latest_block = await self.multichain_client.get_latest_block_number(chain_id)
            
            self.chain_states[chain_id] = {
                'name': chain_config['name'],
                'enabled': chain_config.get('enabled', False),
                'provider': chain_config.get('provider', 'unknown'),
                'latest_block': latest_block or 0,
                'last_processed_block': 0,
                'blocks_processed': 0,
                'transactions_processed': 0,
                'events_processed': 0,
                'errors': 0,
                'avg_block_time': 0.0,
                'tps': 0.0,
                'gas_utilization': 0.0,
                'status': 'connected' if latest_block else 'disconnected',
                'last_update': datetime.now(),
                'processing_lag': 0
            }
            
            logger.debug(f"Initialized state for {chain_id}: {chain_config['name']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize state for {chain_id}: {e}")
            self.chain_states[chain_id] = {
                'name': chain_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def start_monitoring(self, selected_chains: Optional[List[str]] = None):
        """Start the multi-chain monitoring"""
        
        if self.running:
            logger.warning("Monitor is already running")
            return
        
        if selected_chains:
            self.selected_chains = set(selected_chains)
            logger.info(f"Monitoring selected chains: {', '.join(selected_chains)}")
        else:
            logger.info(f"Monitoring all connected chains: {', '.join(self.selected_chains)}")
        
        self.running = True
        self.start_time = time.time()
        
        # Start monitoring with live display
        with Live(self._create_dashboard(), refresh_per_second=1, console=self.console) as live:
            self._live_display = live
            
            try:
                while self.running:
                    if not self.paused:
                        await self._monitoring_cycle()
                    
                    # Update display
                    live.update(self._create_dashboard())
                    
                    # Wait for next cycle
                    await asyncio.sleep(self.poll_interval)
                    
            except KeyboardInterrupt:
                logger.info("Received shutdown signal...")
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            finally:
                await self.stop_monitoring()
    
    async def _monitoring_cycle(self):
        """Execute one monitoring cycle across all selected chains"""
        
        cycle_start = time.time()
        
        try:
            # Update chain states concurrently
            tasks = []
            for chain_id in self.selected_chains:
                if chain_id in self.chain_states:
                    task = asyncio.create_task(self._update_chain_state(chain_id))
                    tasks.append((chain_id, task))
            
            # Wait for all updates
            for chain_id, task in tasks:
                try:
                    await task
                except Exception as e:
                    logger.error(f"Error updating {chain_id}: {e}")
                    self.chain_states[chain_id]['errors'] += 1
                    self.chain_states[chain_id]['status'] = 'error'
                    self.total_errors += 1
            
            # Update analytics periodically (every 30 seconds)
            current_time = time.time()
            if current_time - self.last_analytics_update > 30:
                await self._update_analytics()
                self.last_analytics_update = current_time
            
            # Track performance
            cycle_time = time.time() - cycle_start
            self.performance_history['cycle_time'].append(cycle_time)
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            self.total_errors += 1
    
    async def _update_chain_state(self, chain_id: str):
        """Update state for a single chain"""
        
        try:
            state = self.chain_states[chain_id]
            
            # Get latest block
            latest_block = await self.multichain_client.get_latest_block_number(chain_id)
            if latest_block:
                # Calculate processing lag
                state['processing_lag'] = latest_block - state.get('last_processed_block', 0)
                
                # Update if we have new blocks
                if latest_block > state['latest_block']:
                    old_block = state['latest_block']
                    state['latest_block'] = latest_block
                    
                    # Calculate block time
                    if old_block > 0:
                        time_diff = (datetime.now() - state['last_update']).total_seconds()
                        block_diff = latest_block - old_block
                        if block_diff > 0:
                            state['avg_block_time'] = time_diff / block_diff
                    
                    # Process new blocks (simplified for monitoring)
                    blocks_to_process = min(10, latest_block - state.get('last_processed_block', latest_block - 1))
                    if blocks_to_process > 0:
                        state['blocks_processed'] += blocks_to_process
                        state['last_processed_block'] = latest_block
                        self.total_blocks_processed += blocks_to_process
                        
                        # Estimate transactions (would get real data in full implementation)
                        estimated_txs = blocks_to_process * 50  # Rough estimate
                        state['transactions_processed'] += estimated_txs
                        self.total_transactions_processed += estimated_txs
                
                # Calculate TPS
                if state['avg_block_time'] > 0:
                    estimated_tx_per_block = 50  # Would calculate from real data
                    state['tps'] = estimated_tx_per_block / state['avg_block_time']
                
                state['status'] = 'active'
                state['last_update'] = datetime.now()
                
                # Track performance history
                self.performance_history[f'{chain_id}_block_time'].append(state['avg_block_time'])
                self.performance_history[f'{chain_id}_tps'].append(state['tps'])
                
            else:
                state['status'] = 'disconnected'
                
        except Exception as e:
            logger.error(f"Error updating chain state for {chain_id}: {e}")
            self.chain_states[chain_id]['status'] = 'error'
            raise
    
    async def _update_analytics(self):
        """Update analytics data"""
        
        try:
            if self.analytics:
                analytics_data = await self.analytics.run_comprehensive_analytics(1)  # 1 hour timeframe
                self.analytics_cache = analytics_data
                logger.debug("Updated analytics cache")
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
    
    def _create_dashboard(self) -> Layout:
        """Create the multi-chain monitoring dashboard"""
        
        layout = Layout()
        
        # Create main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Header
        uptime = time.time() - (self.start_time or time.time())
        uptime_str = f"{uptime//3600:.0f}h {(uptime%3600)//60:.0f}m {uptime%60:.0f}s"
        
        header_text = Text()
        header_text.append("🔗 Multi-Chain Blockchain Monitor", style="bold blue")
        header_text.append(f" | Uptime: {uptime_str}", style="dim")
        header_text.append(f" | Chains: {len(self.selected_chains)}", style="cyan")
        header_text.append(f" | Mode: {self.display_mode.title()}", style="yellow")
        
        layout["header"].update(
            Panel(header_text, border_style="blue", title="📊 Dashboard")
        )
        
        # Main content based on display mode
        if self.display_mode == "overview":
            layout["main"].update(self._create_overview_display())
        elif self.display_mode == "detailed":
            layout["main"].update(self._create_detailed_display())
        elif self.display_mode == "analytics":
            layout["main"].update(self._create_analytics_display())
        elif self.display_mode == "comparison":
            layout["main"].update(self._create_comparison_display())
        
        # Footer
        footer_text = Text()
        footer_text.append("🚀 GLQ Multi-Chain Analytics", style="bold green")
        footer_text.append(f" | Processed: {self.total_blocks_processed:,} blocks", style="dim")
        footer_text.append(f" | Errors: {self.total_errors}", style="red" if self.total_errors > 0 else "dim")
        footer_text.append(" | [1] Overview [2] Detailed [3] Analytics [4] Compare [P] Pause [Q] Quit", style="bright_black")
        
        layout["footer"].update(
            Panel(footer_text, border_style="green")
        )
        
        return layout
    
    def _create_overview_display(self) -> Table:
        """Create overview display for all chains"""
        
        table = Table(title="Multi-Chain Overview", expand=True)
        table.add_column("Chain", style="cyan", width=15)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Latest Block", justify="right", width=12)
        table.add_column("Processed", justify="right", width=10)
        table.add_column("TPS", justify="right", width=8)
        table.add_column("Block Time", justify="right", width=10)
        table.add_column("Lag", justify="right", width=8)
        table.add_column("Provider", width=10)
        
        for chain_id in sorted(self.selected_chains):
            if chain_id not in self.chain_states:
                continue
            
            state = self.chain_states[chain_id]
            
            # Status with color coding
            status = state.get('status', 'unknown')
            if status == 'active':
                status_display = "[green]●[/green] Active"
            elif status == 'connected':
                status_display = "[yellow]●[/yellow] Connected"
            elif status == 'disconnected':
                status_display = "[red]●[/red] Disconnected"
            else:
                status_display = "[red]●[/red] Error"
            
            # Lag with color coding
            lag = state.get('processing_lag', 0)
            if lag <= 5:
                lag_display = f"[green]{lag}[/green]"
            elif lag <= 20:
                lag_display = f"[yellow]{lag}[/yellow]"
            else:
                lag_display = f"[red]{lag}[/red]"
            
            table.add_row(
                state.get('name', chain_id),
                status_display,
                f"{state.get('latest_block', 0):,}",
                f"{state.get('blocks_processed', 0):,}",
                f"{state.get('tps', 0):.1f}",
                f"{state.get('avg_block_time', 0):.1f}s",
                lag_display,
                state.get('provider', 'unknown')
            )
        
        return table
    
    def _create_detailed_display(self) -> Columns:
        """Create detailed display with individual chain panels"""
        
        panels = []
        
        for chain_id in sorted(self.selected_chains):
            if chain_id not in self.chain_states:
                continue
            
            state = self.chain_states[chain_id]
            
            # Create detailed info for each chain
            info_text = Text()
            info_text.append(f"Latest Block: {state.get('latest_block', 0):,}\\n", style="white")
            info_text.append(f"Processed: {state.get('blocks_processed', 0):,} blocks\\n", style="cyan")
            info_text.append(f"Transactions: {state.get('transactions_processed', 0):,}\\n", style="green")
            info_text.append(f"TPS: {state.get('tps', 0):.2f}\\n", style="yellow")
            info_text.append(f"Block Time: {state.get('avg_block_time', 0):.2f}s\\n", style="blue")
            info_text.append(f"Provider: {state.get('provider', 'unknown')}\\n", style="magenta")
            info_text.append(f"Errors: {state.get('errors', 0)}", style="red")
            
            # Status color
            status = state.get('status', 'unknown')
            border_style = "green" if status == "active" else "yellow" if status == "connected" else "red"
            
            panel = Panel(
                info_text,
                title=f"{state.get('name', chain_id)} ({chain_id})",
                border_style=border_style,
                expand=False
            )
            
            panels.append(panel)
        
        return Columns(panels, expand=True)
    
    def _create_analytics_display(self) -> Panel:
        """Create analytics display"""
        
        if not self.analytics_cache:
            return Panel(
                Text("Analytics data loading...", justify="center"),
                title="📊 Multi-Chain Analytics",
                border_style="yellow"
            )
        
        # Extract key metrics from analytics cache
        market_overview = self.analytics_cache.get('market_overview', {})
        summary = market_overview.get('summary', {})
        
        content = Text()
        content.append("🌐 Market Overview\\n\\n", style="bold blue")
        
        content.append(f"Total Chains Monitored: {summary.get('total_chains_monitored', 0)}\\n", style="cyan")
        content.append(f"Total Transactions (24h): {summary.get('total_transactions_24h', 0):,}\\n", style="green")
        content.append(f"Total Active Addresses (24h): {summary.get('total_active_addresses_24h', 0):,}\\n", style="yellow")
        content.append(f"Total DEX Volume (24h): ${summary.get('total_dex_volume_24h', 0):,.0f}\\n", style="magenta")
        content.append(f"Cross-Chain Bridge Volume (24h): ${summary.get('cross_chain_bridge_volume_24h', 0):,.0f}\\n", style="blue")
        
        # Chain rankings
        cross_chain_metrics = self.analytics_cache.get('cross_chain_metrics', {})
        rankings = cross_chain_metrics.get('chain_rankings', {})
        
        if rankings:
            content.append("\\n🏆 Chain Rankings\\n\\n", style="bold yellow")
            
            tx_rankings = rankings.get('transaction_volume', {})
            if tx_rankings:
                content.append("Transaction Volume:\\n", style="bold")
                for chain_id, rank in sorted(tx_rankings.items(), key=lambda x: x[1]):
                    chain_name = self.chain_states.get(chain_id, {}).get('name', chain_id)
                    content.append(f"  {rank}. {chain_name}\\n")
            
            tps_rankings = rankings.get('tps', {})
            if tps_rankings:
                content.append("\\nTPS Performance:\\n", style="bold")
                for chain_id, rank in sorted(tps_rankings.items(), key=lambda x: x[1]):
                    chain_name = self.chain_states.get(chain_id, {}).get('name', chain_id)
                    content.append(f"  {rank}. {chain_name}\\n")
        
        return Panel(
            content,
            title="📊 Multi-Chain Analytics",
            border_style="green",
            expand=True
        )
    
    def _create_comparison_display(self) -> Table:
        """Create comparison display"""
        
        table = Table(title="Chain Performance Comparison", expand=True)
        table.add_column("Metric", style="cyan", width=20)
        
        # Add columns for each selected chain
        for chain_id in sorted(self.selected_chains):
            if chain_id in self.chain_states:
                chain_name = self.chain_states[chain_id].get('name', chain_id)
                table.add_column(chain_name, justify="right", width=15)
        
        # Performance metrics comparison
        metrics = [
            ("Latest Block", lambda s: f"{s.get('latest_block', 0):,}"),
            ("TPS", lambda s: f"{s.get('tps', 0):.2f}"),
            ("Block Time (s)", lambda s: f"{s.get('avg_block_time', 0):.2f}"),
            ("Blocks Processed", lambda s: f"{s.get('blocks_processed', 0):,}"),
            ("Transactions", lambda s: f"{s.get('transactions_processed', 0):,}"),
            ("Processing Lag", lambda s: f"{s.get('processing_lag', 0)}"),
            ("Status", lambda s: s.get('status', 'unknown').title()),
            ("Provider", lambda s: s.get('provider', 'unknown').title()),
        ]
        
        for metric_name, metric_func in metrics:
            row = [metric_name]
            
            for chain_id in sorted(self.selected_chains):
                if chain_id in self.chain_states:
                    state = self.chain_states[chain_id]
                    value = metric_func(state)
                    row.append(value)
                else:
                    row.append("N/A")
            
            table.add_row(*row)
        
        return table
    
    async def stop_monitoring(self):
        """Stop the monitoring"""
        
        logger.info("Stopping multi-chain monitor...")
        self.running = False
        
        # Close connections
        if self.multichain_client:
            await self.multichain_client.close()
        
        if self.db_client:
            await self.db_client.close()
        
        if self.analytics:
            await self.analytics.shutdown()
        
        logger.info("Multi-chain monitor stopped")
    
    def pause_monitoring(self):
        """Pause/unpause monitoring"""
        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        logger.info(f"Monitoring {status}")
    
    def switch_display_mode(self, mode: str):
        """Switch display mode"""
        if mode in ["overview", "detailed", "analytics", "comparison"]:
            self.display_mode = mode
            logger.info(f"Switched to {mode} display mode")
    
    def toggle_chain(self, chain_id: str):
        """Toggle monitoring of a specific chain"""
        if chain_id in self.selected_chains:
            self.selected_chains.remove(chain_id)
            logger.info(f"Disabled monitoring for {chain_id}")
        else:
            self.selected_chains.add(chain_id)
            logger.info(f"Enabled monitoring for {chain_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        
        return {
            "running": self.running,
            "paused": self.paused,
            "display_mode": self.display_mode,
            "selected_chains": list(self.selected_chains),
            "total_blocks_processed": self.total_blocks_processed,
            "total_transactions_processed": self.total_transactions_processed,
            "total_errors": self.total_errors,
            "uptime": time.time() - (self.start_time or time.time()),
            "chain_states": self.chain_states,
            "analytics_cache": self.analytics_cache
        }


# Convenience functions for different monitoring modes
async def run_multichain_overview(config: Config, chains: Optional[List[str]] = None):
    """Run multi-chain overview monitoring"""
    
    monitor = MultiChainMonitor(config)
    
    if await monitor.initialize():
        monitor.switch_display_mode("overview")
        await monitor.start_monitoring(chains)


async def run_multichain_detailed(config: Config, chains: Optional[List[str]] = None):
    """Run detailed multi-chain monitoring"""
    
    monitor = MultiChainMonitor(config)
    
    if await monitor.initialize():
        monitor.switch_display_mode("detailed")
        await monitor.start_monitoring(chains)


async def run_multichain_analytics(config: Config):
    """Run multi-chain analytics monitoring"""
    
    monitor = MultiChainMonitor(config)
    
    if await monitor.initialize():
        monitor.switch_display_mode("analytics")
        await monitor.start_monitoring()


async def run_chain_comparison(config: Config):
    """Run chain performance comparison monitoring"""
    
    monitor = MultiChainMonitor(config)
    
    if await monitor.initialize():
        monitor.switch_display_mode("comparison")
        await monitor.start_monitoring()