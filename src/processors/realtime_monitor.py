"""
Real-time Blockchain Monitor
Monitors GLQ Chain for new blocks and processes them immediately.
"""

import asyncio
import logging
import time
import sys
from typing import Optional, Dict, Any, Set
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.blockchain_client import BlockchainClient
from core.influxdb_client import BlockchainInfluxDB
from core.config import Config
from analytics.advanced_analytics import AdvancedAnalytics
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()
logger = logging.getLogger(__name__)


class RealtimeMonitor:
    """Real-time blockchain monitor for GLQ Chain."""
    
    def __init__(self, config: Config):
        self.config = config
        self.blockchain_client = BlockchainClient(config)
        
        # InfluxDB client
        self.db_client = None
        if config.influxdb_token:
            self.db_client = BlockchainInfluxDB(config)
            
        # Advanced Analytics coordinator
        self.analytics = None
        if self.db_client and config.is_analytics_enabled():
            realtime_config = config.get_analytics_realtime_config()
            if realtime_config.get('enabled', True):
                self.analytics = AdvancedAnalytics(
                    blockchain_client=self.blockchain_client,
                    db_client=self.db_client,
                    config=config
                )
                # Store analytics performance settings
                self.analytics_max_time = realtime_config.get('max_processing_time', 5.0)
                self.analytics_skip_on_timeout = realtime_config.get('skip_on_timeout', True)
        
        # Monitoring configuration
        self.poll_interval = config.poll_interval or 2
        self.confirmation_blocks = config.confirmation_blocks or 2
        
        # State tracking
        self.last_processed_block = 0
        self.latest_network_block = 0
        self.processed_blocks: Set[int] = set()
        
        # Statistics
        self.stats = {
            'start_time': None,
            'blocks_processed': 0,
            'transactions_processed': 0,
            'events_processed': 0,
            'errors': 0,
            'processing_lag': 0,
            'avg_block_time': 0.0,
            'last_block_time': None,
            'blocks_per_minute': 0.0,
            'uptime': 0.0,
            # Analytics statistics
            'analytics_enabled': config.is_analytics_enabled() and self.analytics is not None,
            'token_transfers_found': 0,
            'dex_swaps_found': 0,
            'liquidity_events_found': 0,
            'defi_events_found': 0,
            'total_analytics_events': 0,
            'analytics_timeouts': 0,
            'analytics_processing_time': 0.0
        }
        
        # Last analytics results for display
        self._last_analytics = {}
        
        # Performance tracking
        self.recent_block_times = []
        self.recent_processing_times = []
        
        # Control flags
        self.running = False
        self.paused = False
        
    async def initialize(self) -> bool:
        """Initialize connections and determine starting point."""
        logger.info("Initializing real-time monitor...")
        
        # Connect to blockchain
        blockchain_connected = await self.blockchain_client.connect()
        if not blockchain_connected:
            logger.error("Failed to connect to blockchain")
            return False
            
        # Connect to database
        db_connected = True
        if self.db_client:
            db_connected = await self.db_client.connect()
            if not db_connected:
                logger.warning("Database connection failed, monitoring will continue without storage")
                
        # Determine starting block
        await self._determine_starting_block()
        
        logger.info(
            f"Real-time monitor initialized - Chain: {blockchain_connected}, "
            f"Database: {db_connected}, Starting from block: {self.last_processed_block}"
        )
        
        return True
        
    async def _determine_starting_block(self):
        """Determine which block to start monitoring from."""
        try:
            # Get latest network block
            self.latest_network_block = await self.blockchain_client.get_latest_block_number()
            
            # Get latest processed block from database
            if self.db_client:
                try:
                    latest_db_block = self.db_client.query_latest_block()
                    if latest_db_block is not None:
                        self.last_processed_block = latest_db_block
                        logger.info(f"Resuming from database block {latest_db_block}")
                    else:
                        # Start from recent blocks if no data in DB
                        self.last_processed_block = max(0, self.latest_network_block - 100)
                        logger.info(f"No database data found, starting from block {self.last_processed_block}")
                except Exception as e:
                    logger.warning(f"Could not query database for latest block: {e}")
                    self.last_processed_block = max(0, self.latest_network_block - 100)
            else:
                # Start from recent blocks if no database
                self.last_processed_block = max(0, self.latest_network_block - 100)
                
        except Exception as e:
            logger.error(f"Error determining starting block: {e}")
            self.last_processed_block = 0
            
    async def start_monitoring(self):
        """Start the real-time monitoring loop."""
        if self.running:
            logger.warning("Monitor is already running")
            return
            
        logger.info("Starting real-time blockchain monitoring...")
        self.running = True
        self.stats['start_time'] = time.time()
        
        # Start monitoring with live display
        with Live(self._create_status_table(), refresh_per_second=1, console=console) as live:
            self._live_display = live
            
            try:
                while self.running:
                    if not self.paused:
                        await self._monitoring_cycle()
                    
                    # Update display
                    live.update(self._create_status_table())
                    
                    # Wait for next cycle
                    await asyncio.sleep(self.poll_interval)
                    
            except KeyboardInterrupt:
                logger.info("Received shutdown signal...")
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            finally:
                await self.stop_monitoring()
                
    async def _monitoring_cycle(self):
        """Execute one monitoring cycle."""
        cycle_start = time.time()
        
        try:
            # Get latest network block
            current_latest = await self.blockchain_client.get_latest_block_number()
            if current_latest is None:
                self.stats['errors'] += 1
                logger.warning("Could not get latest block number")
                return
                
            self.latest_network_block = current_latest
            
            # Calculate processing lag
            self.stats['processing_lag'] = max(0, self.latest_network_block - self.last_processed_block)
            
            # Process new blocks (with confirmation delay)
            target_block = self.latest_network_block - self.confirmation_blocks
            
            if target_block > self.last_processed_block:
                await self._process_new_blocks(self.last_processed_block + 1, target_block)
                
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            self.stats['errors'] += 1
            
        # Track cycle performance
        cycle_time = time.time() - cycle_start
        self.recent_processing_times.append(cycle_time)
        if len(self.recent_processing_times) > 20:  # Keep last 20 measurements
            self.recent_processing_times.pop(0)
            
    async def _process_new_blocks(self, start_block: int, end_block: int):
        """Process a range of new blocks."""
        for block_num in range(start_block, end_block + 1):
            if block_num in self.processed_blocks:
                continue  # Skip already processed blocks
                
            process_start = time.time()
            
            try:
                # Get block data
                block_data = await self.blockchain_client.get_block(block_num, include_transactions=True)
                
                if block_data is None:
                    logger.warning(f"Could not retrieve block {block_num}")
                    self.stats['errors'] += 1
                    continue
                    
                # Process the block
                await self._process_single_block(block_data, block_num)
                
                # Update tracking
                self.processed_blocks.add(block_num)
                self.last_processed_block = block_num
                self.stats['blocks_processed'] += 1
                self.stats['last_block_time'] = datetime.now()
                
                # Calculate block time if we have previous data
                if len(self.recent_block_times) > 0:
                    block_time = process_start - self.recent_block_times[-1]
                    if block_time > 0:
                        self.stats['avg_block_time'] = sum(
                            time.time() - bt for bt in self.recent_block_times[-10:]
                        ) / min(10, len(self.recent_block_times))
                        
                self.recent_block_times.append(process_start)
                if len(self.recent_block_times) > 20:
                    self.recent_block_times.pop(0)
                    
            except Exception as e:
                logger.error(f"Error processing block {block_num}: {e}")
                self.stats['errors'] += 1
                
        # Clean up old processed block tracking (keep last 1000)
        if len(self.processed_blocks) > 1000:
            old_blocks = sorted(self.processed_blocks)[:len(self.processed_blocks) - 1000]
            for old_block in old_blocks:
                self.processed_blocks.discard(old_block)
                
    async def _process_single_block(self, block_data: Dict[str, Any], block_number: int):
        """Process a single block and its transactions, including advanced analytics."""
        try:
            # Store block data
            if self.db_client:
                self.db_client.write_block(block_data)
            
            # Run advanced analytics on the block if enabled
            if self.analytics:
                analytics_start = time.time()
                try:
                    # Compute block timestamp
                    ts = datetime.fromtimestamp(int(block_data.get('timestamp', '0x0'), 16), tz=timezone.utc)
                    
                    # Run analytics with timeout if configured
                    if hasattr(self, 'analytics_max_time') and self.analytics_max_time > 0:
                        # Use asyncio.wait_for for timeout
                        block_results = await asyncio.wait_for(
                            self.analytics.analyze_block(block_data, ts),
                            timeout=self.analytics_max_time
                        )
                    else:
                        # No timeout
                        block_results = await self.analytics.analyze_block(block_data, ts)
                    
                    # Track analytics processing time
                    analytics_time = time.time() - analytics_start
                    self.stats['analytics_processing_time'] = (
                        self.stats['analytics_processing_time'] * 0.9 + analytics_time * 0.1
                    )
                    
                    # Update analytics statistics
                    self.stats['token_transfers_found'] += block_results.get('token_transfers', 0)
                    self.stats['dex_swaps_found'] += block_results.get('dex_swaps', 0)
                    self.stats['liquidity_events_found'] += block_results.get('liquidity_events', 0)
                    defi_events = block_results.get('lending_events', 0) + block_results.get('staking_events', 0) + block_results.get('yield_events', 0)
                    self.stats['defi_events_found'] += defi_events
                    self.stats['total_analytics_events'] += block_results.get('total_events_found', 0)
                    
                    # Stash last analytics results for UI
                    self._last_analytics = block_results
                    
                except asyncio.TimeoutError:
                    self.stats['analytics_timeouts'] += 1
                    analytics_time = time.time() - analytics_start
                    logger.warning(f"Analytics timeout for block {block_number} after {analytics_time:.2f}s")
                    if not getattr(self, 'analytics_skip_on_timeout', True):
                        raise  # Re-raise if we shouldn't skip
                except Exception as ae:
                    analytics_time = time.time() - analytics_start
                    self.stats['analytics_processing_time'] = (
                        self.stats['analytics_processing_time'] * 0.9 + analytics_time * 0.1
                    )
                    logger.debug(f"Advanced analytics failed for block {block_number}: {ae}")
            
            # Process transactions (DB storage and events)
            transactions = block_data.get('transactions', [])
            for tx in transactions:
                if isinstance(tx, dict):  # Full transaction object
                    await self._process_transaction(tx, block_number)
                    self.stats['transactions_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing block {block_number}: {e}")
            raise
            
    async def _process_transaction(self, tx_data: Dict[str, Any], block_number: int):
        """Process a single transaction."""
        try:
            # Get transaction receipt for complete data
            receipt = await self.blockchain_client.get_transaction_receipt(tx_data['hash'])
            
            gas_used = None
            status = "pending"
            
            if receipt:
                gas_used = int(receipt.get('gasUsed', '0x0'), 16)
                status = "success" if receipt.get('status') == '0x1' else "failed"
                
                # Process logs/events if present
                logs = receipt.get('logs', [])
                for log in logs:
                    if self.db_client:
                        self.db_client.write_event(log, block_number, tx_data['hash'])
                    self.stats['events_processed'] += 1
                    
            # Store transaction data
            if self.db_client:
                self.db_client.write_transaction(tx_data, block_number, status, gas_used)
                
        except Exception as e:
            logger.debug(f"Error processing transaction {tx_data.get('hash', 'unknown')}: {e}")
            
    def _create_status_table(self) -> Panel:
        """Create a rich status display table."""
        # Calculate uptime and rates
        if self.stats['start_time']:
            self.stats['uptime'] = time.time() - self.stats['start_time']
            if self.stats['uptime'] > 60:  # More than 1 minute
                self.stats['blocks_per_minute'] = (self.stats['blocks_processed'] / self.stats['uptime']) * 60
                
        # Create main status table
        table = Table(title="🔄 GLQ Chain Real-time Monitor", show_header=True)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="green", width=30)
        table.add_column("Details", style="yellow", width=25)
        
        # Connection status
        status_color = "green" if self.running and not self.paused else "red"
        status_text = "🟢 MONITORING" if self.running and not self.paused else "🔴 STOPPED"
        table.add_row("Status", f"[{status_color}]{status_text}[/{status_color}]", "")
        
        # Block information
        table.add_row(
            "Latest Network Block", 
            f"{self.latest_network_block:,}",
            f"Chain ID: 614"
        )
        table.add_row(
            "Last Processed Block", 
            f"{self.last_processed_block:,}",
            f"Lag: {self.stats['processing_lag']} blocks"
        )
        
        # Processing statistics
        table.add_row(
            "Blocks Processed",
            f"{self.stats['blocks_processed']:,}",
            f"Rate: {self.stats['blocks_per_minute']:.2f}/min"
        )
        table.add_row(
            "Transactions Processed", 
            f"{self.stats['transactions_processed']:,}",
            ""
        )
        table.add_row(
            "Events Processed",
            f"{self.stats['events_processed']:,}",
            ""
        )
        
        # Analytics metrics section
        if self.stats.get('analytics_enabled', False):
            table.add_row("", "", "")  # Separator
            table.add_row(
                "📊 Analytics Summary",
                f"Total: {self.stats.get('total_analytics_events', 0):,}",
                "Advanced Analytics"
            )
            table.add_row(
                "🪙 Token Transfers",
                f"{self.stats.get('token_transfers_found', 0):,}",
                "ERC20/721/1155"
            )
            table.add_row(
                "🔄 DEX Swaps",
                f"{self.stats.get('dex_swaps_found', 0):,}",
                "Uniswap V2/V3"
            )
            table.add_row(
                "💧 Liquidity Events",
                f"{self.stats.get('liquidity_events_found', 0):,}",
                "Add/Remove LP"
            )
            table.add_row(
                "🏦 DeFi Events",
                f"{self.stats.get('defi_events_found', 0):,}",
                "Lending/Staking/Yield"
            )
            
            # Analytics performance metrics
            if self.stats.get('analytics_processing_time', 0) > 0:
                table.add_row(
                    "🏦 Avg Analytics",
                    f"{self.stats.get('analytics_processing_time', 0):.3f}s",
                    f"Max: {getattr(self, 'analytics_max_time', 'N/A')}s"
                )
            
            if self.stats.get('analytics_timeouts', 0) > 0:
                table.add_row(
                    "⚠️ Analytics Timeouts",
                    f"{self.stats.get('analytics_timeouts', 0):,}",
                    "Processing Skipped"
                )
            
        table.add_row("", "", "")  # Separator
        table.add_row("Errors", f"{self.stats['errors']:,}", "")
        
        # Performance metrics
        uptime_str = f"{int(self.stats['uptime']//3600):02d}:{int((self.stats['uptime']%3600)//60):02d}:{int(self.stats['uptime']%60):02d}"
        table.add_row("Uptime", uptime_str, "")
        
        if self.stats['last_block_time']:
            time_since = datetime.now() - self.stats['last_block_time']
            table.add_row("Last Block", f"{time_since.seconds}s ago", "")
            
        # Average processing time
        if self.recent_processing_times:
            avg_processing = sum(self.recent_processing_times) / len(self.recent_processing_times)
            table.add_row("Avg Cycle Time", f"{avg_processing:.3f}s", f"Poll: {self.poll_interval}s")
            
        return Panel(table, title="GLQ Chain Analytics - Real-time Monitor", border_style="blue")
        
    async def stop_monitoring(self):
        """Stop the monitoring process gracefully."""
        logger.info("Stopping real-time monitor...")
        self.running = False
        
        # Close connections
        if self.blockchain_client:
            self.blockchain_client.close()
        if self.db_client:
            self.db_client.close()
            
        logger.info("Real-time monitor stopped")
        
    def pause_monitoring(self):
        """Pause the monitoring (keep connections alive)."""
        self.paused = True
        logger.info("Monitoring paused")
        
    def resume_monitoring(self):
        """Resume paused monitoring."""
        self.paused = False
        logger.info("Monitoring resumed")
        
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            'running': self.running,
            'paused': self.paused,
            'last_processed_block': self.last_processed_block,
            'latest_network_block': self.latest_network_block,
            'processing_lag': self.stats['processing_lag'],
            'statistics': self.stats.copy(),
            'uptime': self.stats['uptime']
        }


async def main():
    """Main function to run real-time monitoring."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/realtime_monitor.log')
        ]
    )
    
    console.print(Panel(
        Text("🚀 GLQ Chain Real-time Monitor Starting...", style="bold green"),
        title="Blockchain Analytics",
        border_style="green"
    ))
    
    # Load configuration
    config = Config()
    
    # Create and initialize monitor
    monitor = RealtimeMonitor(config)
    
    try:
        # Initialize connections
        if not await monitor.initialize():
            console.print("[bold red]❌ Failed to initialize monitor![/bold red]")
            return False
            
        # Start monitoring
        await monitor.start_monitoring()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Shutdown requested...[/yellow]")
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        console.print(f"[bold red]❌ Monitor failed: {e}[/bold red]")
        return False
    finally:
        await monitor.stop_monitoring()
        
    console.print("[bold green]✅ Monitor shutdown complete![/bold green]")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! 👋[/yellow]")