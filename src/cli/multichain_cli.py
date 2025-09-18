"""
Multi-Chain CLI Interface

Enhanced command-line interface for managing multi-chain blockchain operations,
including individual chain management, analytics, monitoring, and reporting.
"""

import asyncio
import argparse
import sys
import json
import csv
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import logging

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import track, Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from core.config import Config
from core.multichain_client import MultiChainClient
from core.multichain_influxdb_client import MultiChainInfluxDB
from processors.multichain_processor import MultiChainProcessor
from processors.multichain_monitor import MultiChainMonitor
from analytics.chain_analytics import MultiChainAnalyticsOrchestrator

console = Console()
logger = logging.getLogger(__name__)


class MultiChainCLI:
    """Enhanced CLI for multi-chain operations"""
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.multichain_client: Optional[MultiChainClient] = None
        self.db_client: Optional[MultiChainInfluxDB] = None
        self.analytics: Optional[MultiChainAnalyticsOrchestrator] = None
        
    async def initialize(self, config_path: Optional[str] = None):
        """Initialize the CLI with configuration"""
        try:
            self.config = Config(config_path) if config_path else Config()
            console.print("✅ Configuration loaded successfully")
            return True
        except Exception as e:
            console.print(f"[red]❌ Failed to load configuration: {e}[/red]")
            return False
    
    async def connect_clients(self):
        """Connect to multi-chain clients"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                
                # Connect multi-chain client
                task1 = progress.add_task("Connecting to blockchain networks...", total=None)
                self.multichain_client = MultiChainClient(self.config)
                await self.multichain_client.connect()
                progress.remove_task(task1)
                
                # Connect database client
                task2 = progress.add_task("Connecting to InfluxDB...", total=None)
                self.db_client = MultiChainInfluxDB(self.config)
                await self.db_client.connect()
                progress.remove_task(task2)
                
                # Initialize analytics
                task3 = progress.add_task("Initializing analytics...", total=None)
                self.analytics = MultiChainAnalyticsOrchestrator(self.config)
                await self.analytics.initialize()
                progress.remove_task(task3)
            
            console.print("✅ All clients connected successfully")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Failed to connect clients: {e}[/red]")
            return False
    
    async def close_connections(self):
        """Close all connections"""
        if self.multichain_client:
            await self.multichain_client.close()
        if self.db_client:
            await self.db_client.close()
        if self.analytics:
            await self.analytics.shutdown()
    
    async def cmd_status(self, args):
        """Show multi-chain status"""
        console.print(Panel(
            Text("🔗 Multi-Chain System Status", style="bold blue"),
            border_style="blue"
        ))
        
        if not await self.connect_clients():
            return False
        
        try:
            # Get connected chains
            connected_chains = self.multichain_client.get_connected_chains()
            all_chains = list(self.config.chains.keys())
            
            # Create status table
            table = Table(title="Chain Connection Status", expand=True)
            table.add_column("Chain", style="cyan", width=20)
            table.add_column("Status", justify="center", width=12)
            table.add_column("Latest Block", justify="right", width=15)
            table.add_column("Provider", width=12)
            table.add_column("Chain ID", justify="right", width=10)
            
            for chain_id in all_chains:
                chain_config = self.config.chains[chain_id]
                
                if chain_id in connected_chains:
                    try:
                        latest_block = await self.multichain_client.get_latest_block_number(chain_id)
                        chain_info = await self.multichain_client.get_chain_info(chain_id)
                        
                        status = "[green]●[/green] Connected"
                        block_display = f"{latest_block:,}" if latest_block else "N/A"
                        actual_chain_id = chain_info.get('chain_id', 'Unknown')
                        
                    except Exception as e:
                        status = "[yellow]●[/yellow] Error"
                        block_display = f"Error: {str(e)[:30]}..."
                        actual_chain_id = "Unknown"
                else:
                    status = "[red]●[/red] Disconnected"
                    block_display = "N/A"
                    actual_chain_id = "N/A"
                
                table.add_row(
                    chain_config['name'],
                    status,
                    block_display,
                    chain_config.get('provider', 'unknown'),
                    str(actual_chain_id)
                )
            
            console.print(table)
            
            # Summary
            console.print(f"\n📊 Summary: {len(connected_chains)}/{len(all_chains)} chains connected")
            
            await self.close_connections()
            return True
            
        except Exception as e:
            console.print(f"[red]Error getting status: {e}[/red]")
            return False
    
    async def cmd_sync(self, args):
        """Run historical synchronization"""
        console.print(Panel(
            Text("🔄 Multi-Chain Historical Synchronization", style="bold green"),
            border_style="green"
        ))
        
        if not await self.connect_clients():
            return False
        
        try:
            processor = MultiChainProcessor(self.config)
            
            # Parse chain list
            chains = None
            if args.chains:
                chains = [chain.strip() for chain in args.chains.split(',')]
                console.print(f"📍 Target chains: [yellow]{', '.join(chains)}[/yellow]")
            
            if args.max_blocks:
                console.print(f"📊 Max blocks per chain: [cyan]{args.max_blocks:,}[/cyan]")
            
            console.print("\n🚀 Starting synchronization...\n")
            
            success = await processor.process_historical_data(
                chains=chains,
                max_blocks=args.max_blocks
            )
            
            if success:
                console.print("\n✅ [bold green]Synchronization completed successfully![/bold green]")
            else:
                console.print("\n❌ [bold red]Synchronization failed![/bold red]")
                return False
            
            await self.close_connections()
            return True
            
        except Exception as e:
            console.print(f"\n[red]❌ Synchronization error: {e}[/red]")
            return False
    
    async def cmd_monitor(self, args):
        """Start real-time monitoring"""
        console.print(Panel(
            Text("👀 Multi-Chain Real-Time Monitor", style="bold magenta"),
            border_style="magenta"
        ))
        
        monitor = MultiChainMonitor(self.config)
        
        if not await monitor.initialize():
            console.print("[red]❌ Failed to initialize monitor[/red]")
            return False
        
        # Parse chains
        chains = None
        if args.chains:
            chains = [chain.strip() for chain in args.chains.split(',')]
        
        # Set display mode
        if hasattr(args, 'mode') and args.mode:
            monitor.switch_display_mode(args.mode)
        
        try:
            await monitor.start_monitoring(chains)
            return True
        except KeyboardInterrupt:
            console.print("\n⚠️ Monitoring stopped by user")
            return True
        except Exception as e:
            console.print(f"\n[red]❌ Monitoring error: {e}[/red]")
            return False
    
    async def cmd_analytics(self, args):
        """Run analytics operations"""
        console.print(Panel(
            Text("📊 Multi-Chain Analytics", style="bold blue"),
            border_style="blue"
        ))
        
        if not await self.connect_clients():
            return False
        
        try:
            timeframe = getattr(args, 'hours', 24)
            console.print(f"⏱️ Analyzing data for the last {timeframe} hours...\n")
            
            # Run comprehensive analytics
            results = await self.analytics.run_comprehensive_analytics(timeframe)
            
            # Display results
            await self._display_analytics_results(results)
            
            # Export if requested
            if hasattr(args, 'export') and args.export:
                await self._export_json(results, args.export)
            
            await self.close_connections()
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Analytics error: {e}[/red]")
            return False
    
    async def cmd_chain(self, args):
        """Individual chain operations"""
        console.print(Panel(
            Text(f"⛓️ Chain Operation: {args.chain_id}", style="bold cyan"),
            border_style="cyan"
        ))
        
        if not await self.connect_clients():
            return False
        
        chain_id = args.chain_id
        
        # Verify chain exists
        if chain_id not in self.config.chains:
            console.print(f"[red]❌ Unknown chain: {chain_id}[/red]")
            console.print(f"Available chains: {', '.join(self.config.chains.keys())}")
            return False
        
        try:
            if args.operation == 'info':
                await self._chain_info(chain_id)
            elif args.operation == 'blocks':
                await self._chain_blocks(chain_id, args)
            elif args.operation == 'transactions':
                await self._chain_transactions(chain_id, args)
            elif args.operation == 'health':
                await self._chain_health(chain_id)
            else:
                console.print(f"[red]❌ Unknown operation: {args.operation}[/red]")
                return False
            
            await self.close_connections()
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Chain operation error: {e}[/red]")
            return False
    
    async def cmd_compare(self, args):
        """Compare chains"""
        console.print(Panel(
            Text("🔍 Multi-Chain Comparison", style="bold yellow"),
            border_style="yellow"
        ))
        
        if not await self.connect_clients():
            return False
        
        try:
            # Parse chains to compare
            chains = [chain.strip() for chain in args.chains.split(',')]
            
            console.print(f"🔗 Comparing chains: [cyan]{', '.join(chains)}[/cyan]\n")
            
            # Get latest data for each chain
            comparison_data = {}
            
            for chain_id in chains:
                if chain_id not in self.config.chains:
                    console.print(f"[yellow]⚠️ Skipping unknown chain: {chain_id}[/yellow]")
                    continue
                
                try:
                    latest_block = await self.multichain_client.get_latest_block_number(chain_id)
                    chain_info = await self.multichain_client.get_chain_info(chain_id)
                    
                    comparison_data[chain_id] = {
                        'name': self.config.chains[chain_id]['name'],
                        'latest_block': latest_block,
                        'chain_id_actual': chain_info.get('chain_id', 'Unknown'),
                        'provider': self.config.chains[chain_id].get('provider', 'unknown'),
                        'status': 'connected'
                    }
                    
                except Exception as e:
                    comparison_data[chain_id] = {
                        'name': self.config.chains[chain_id]['name'],
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Create comparison table
            table = Table(title="Chain Comparison", expand=True)
            table.add_column("Metric", style="cyan", width=20)
            
            for chain_id in chains:
                if chain_id in comparison_data:
                    table.add_column(comparison_data[chain_id]['name'], justify="right", width=15)
            
            # Add rows
            metrics = [
                ("Status", lambda data: data.get('status', 'unknown').title()),
                ("Latest Block", lambda data: f"{data.get('latest_block', 0):,}" if data.get('latest_block') else "N/A"),
                ("Chain ID", lambda data: str(data.get('chain_id_actual', 'N/A'))),
                ("Provider", lambda data: data.get('provider', 'unknown').title()),
            ]
            
            for metric_name, metric_func in metrics:
                row = [metric_name]
                for chain_id in chains:
                    if chain_id in comparison_data:
                        row.append(metric_func(comparison_data[chain_id]))
                    else:
                        row.append("N/A")
                table.add_row(*row)
            
            console.print(table)
            
            await self.close_connections()
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Comparison error: {e}[/red]")
            return False
    
    async def cmd_export(self, args):
        """Export data"""
        console.print(Panel(
            Text("💾 Data Export", style="bold green"),
            border_style="green"
        ))
        
        if not await self.connect_clients():
            return False
        
        try:
            # Run analytics to get data
            console.print("📊 Gathering analytics data...")
            results = await self.analytics.run_comprehensive_analytics(args.hours or 24)
            
            # Export based on format
            if args.format == 'json':
                await self._export_json(results, args.output)
            elif args.format == 'csv':
                await self._export_csv(results, args.output)
            else:
                console.print(f"[red]❌ Unsupported format: {args.format}[/red]")
                return False
            
            await self.close_connections()
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Export error: {e}[/red]")
            return False
    
    async def _chain_info(self, chain_id: str):
        """Display chain information"""
        chain_config = self.config.chains[chain_id]
        
        try:
            chain_info = await self.multichain_client.get_chain_info(chain_id)
            latest_block = await self.multichain_client.get_latest_block_number(chain_id)
            
            info_text = Text()
            info_text.append(f"Chain Name: {chain_config['name']}\\n", style="cyan")
            info_text.append(f"Chain ID: {chain_info.get('chain_id', 'Unknown')}\\n", style="green")
            info_text.append(f"Provider: {chain_config.get('provider', 'unknown')}\\n", style="yellow")
            info_text.append(f"Latest Block: {latest_block:,}\\n", style="magenta")
            info_text.append(f"Status: Connected\\n", style="green")
            
            if 'rpc_url' in chain_config:
                info_text.append(f"RPC URL: {chain_config['rpc_url'][:50]}...\\n", style="dim")
            
            console.print(Panel(info_text, title=f"Chain Info: {chain_id}", border_style="cyan"))
            
        except Exception as e:
            console.print(f"[red]❌ Failed to get chain info: {e}[/red]")
    
    async def _chain_health(self, chain_id: str):
        """Check chain health"""
        try:
            if hasattr(self.multichain_client, 'health_check'):
                health = await self.multichain_client.health_check()
                chain_health = health.get(chain_id, {})
                
                status = chain_health.get('status', 'unknown')
                if status == 'healthy':
                    console.print(f"✅ [green]{chain_id} is healthy[/green]")
                    if 'info' in chain_health:
                        info = chain_health['info']
                        console.print(f"   Latest block: {info.get('latest_block', 'unknown'):,}")
                        console.print(f"   Chain ID: {info.get('chain_id', 'unknown')}")
                else:
                    console.print(f"❌ [red]{chain_id} is unhealthy[/red]")
                    if 'error' in chain_health:
                        console.print(f"   Error: {chain_health['error']}")
            else:
                # Fallback health check
                latest_block = await self.multichain_client.get_latest_block_number(chain_id)
                if latest_block:
                    console.print(f"✅ [green]{chain_id} is responsive[/green]")
                    console.print(f"   Latest block: {latest_block:,}")
                else:
                    console.print(f"❌ [red]{chain_id} is not responsive[/red]")
                    
        except Exception as e:
            console.print(f"❌ [red]Health check failed for {chain_id}: {e}[/red]")
    
    async def _chain_blocks(self, chain_id: str, args):
        """Display recent blocks for a chain"""
        try:
            latest_block = await self.multichain_client.get_latest_block_number(chain_id)
            if not latest_block:
                console.print(f"[red]❌ Could not get latest block for {chain_id}[/red]")
                return
            
            limit = getattr(args, 'limit', 10)
            start_block = max(1, latest_block - limit + 1)
            
            console.print(f"\n📦 Latest {limit} blocks for {chain_id}:")
            console.print(f"Block range: {start_block:,} to {latest_block:,}\n")
            
            table = Table(title=f"Recent Blocks - {self.config.chains[chain_id]['name']}")
            table.add_column("Block", justify="right", width=12)
            table.add_column("Transactions", justify="right", width=12)
            table.add_column("Gas Used", justify="right", width=15)
            table.add_column("Size (bytes)", justify="right", width=12)
            
            # This would require implementing batch block retrieval
            # For now, show a summary
            for block_num in range(start_block, latest_block + 1):
                # Mock data - in real implementation would fetch actual block data
                table.add_row(
                    f"{block_num:,}",
                    "~50",  # Estimated transactions
                    "~15M",  # Estimated gas used
                    "~32KB"  # Estimated size
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ Error getting blocks for {chain_id}: {e}[/red]")
    
    async def _chain_transactions(self, chain_id: str, args):
        """Display recent transactions for a chain"""
        try:
            latest_block = await self.multichain_client.get_latest_block_number(chain_id)
            if not latest_block:
                console.print(f"[red]❌ Could not get latest block for {chain_id}[/red]")
                return
            
            limit = getattr(args, 'limit', 10)
            
            console.print(f"\n💸 Recent transaction summary for {chain_id}:")
            console.print(f"Latest block: {latest_block:,}\n")
            
            # This would require implementing transaction retrieval
            # For now, show a summary message
            console.print(f"[yellow]ℹ️ Transaction details require block-by-block processing.[/yellow]")
            console.print(f"[cyan]💡 Use the monitoring dashboard for real-time transaction data.[/cyan]")
            console.print(f"[dim]Command: python start_multichain_monitor.py --chains {chain_id} --mode detailed[/dim]")
            
        except Exception as e:
            console.print(f"[red]❌ Error getting transactions for {chain_id}: {e}[/red]")
    
    async def _display_analytics_results(self, results: Dict[str, Any]):
        """Display analytics results"""
        
        # Market Overview
        market_overview = results.get('market_overview', {})
        summary = market_overview.get('summary', {})
        
        # Summary panel
        summary_text = Text()
        summary_text.append(f"Chains Monitored: {summary.get('total_chains_monitored', 0)}\\n", style="cyan")
        summary_text.append(f"Total Transactions (24h): {summary.get('total_transactions_24h', 0):,}\\n", style="green")
        summary_text.append(f"Active Addresses (24h): {summary.get('total_active_addresses_24h', 0):,}\\n", style="yellow")
        summary_text.append(f"DEX Volume (24h): ${summary.get('total_dex_volume_24h', 0):,.0f}\\n", style="magenta")
        summary_text.append(f"Bridge Volume (24h): ${summary.get('cross_chain_bridge_volume_24h', 0):,.0f}", style="blue")
        
        console.print(Panel(summary_text, title="📈 Market Summary", border_style="green"))
        
        # Chain Rankings
        cross_chain_metrics = results.get('cross_chain_metrics', {})
        rankings = cross_chain_metrics.get('chain_rankings', {})
        
        if rankings:
            console.print("\n🏆 Chain Rankings:")
            
            for metric, ranking in rankings.items():
                console.print(f"\n[bold]{metric.replace('_', ' ').title()}:[/bold]")
                for chain_id, rank in sorted(ranking.items(), key=lambda x: x[1]):
                    chain_name = self.config.chains.get(chain_id, {}).get('name', chain_id)
                    console.print(f"  {rank}. [cyan]{chain_name}[/cyan]")
    
    async def _export_json(self, data: Dict[str, Any], filename: str):
        """Export data as JSON"""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        console.print(f"✅ Data exported to [cyan]{filename}[/cyan]")
    
    async def _export_csv(self, data: Dict[str, Any], filename: str):
        """Export data as CSV"""
        # Extract summary data for CSV
        market_overview = data.get('market_overview', {})
        summary = market_overview.get('summary', {})
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Value'])
            
            for key, value in summary.items():
                writer.writerow([key.replace('_', ' ').title(), value])
        
        console.print(f"✅ Summary data exported to [cyan]{filename}[/cyan]")


def create_parser():
    """Create the argument parser"""
    
    parser = argparse.ArgumentParser(
        description="Multi-Chain Blockchain Analytics CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python multichain.bat status                                      # Show all chain status
  multichain.bat sync --chains ethereum,polygon                     # Sync specific chains  
  multichain.bat monitor --mode analytics                           # Start analytics monitor
  multichain.bat analytics --hours 48 --export results.json        # Run analytics and export
  multichain.bat chain glq info                                     # Get GLQ chain info
  multichain.bat compare --chains ethereum,polygon,base             # Compare chains
  multichain.bat export --format json --output data.json --hours 24 # Export analytics data
        """
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration file',
        default='config/config.yaml'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show multi-chain status')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Run historical synchronization')
    sync_parser.add_argument('--chains', help='Comma-separated list of chain IDs')
    sync_parser.add_argument('--max-blocks', type=int, help='Maximum blocks per chain')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start real-time monitoring')
    monitor_parser.add_argument('--chains', help='Comma-separated list of chain IDs')
    monitor_parser.add_argument('--mode', choices=['overview', 'detailed', 'analytics', 'comparison'], 
                              default='overview', help='Display mode')
    
    # Analytics command
    analytics_parser = subparsers.add_parser('analytics', help='Run analytics')
    analytics_parser.add_argument('--hours', type=int, default=24, help='Time frame in hours')
    analytics_parser.add_argument('--export', help='Export results to file')
    
    # Chain command
    chain_parser = subparsers.add_parser('chain', help='Individual chain operations')
    chain_parser.add_argument('chain_id', help='Chain ID')
    chain_parser.add_argument('operation', choices=['info', 'blocks', 'transactions', 'health'], 
                            help='Operation to perform')
    chain_parser.add_argument('--limit', type=int, default=10, help='Limit for results')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare chains')
    compare_parser.add_argument('--chains', required=True, help='Comma-separated list of chain IDs')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export analytics data')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Export format')
    export_parser.add_argument('--output', required=True, help='Output filename')
    export_parser.add_argument('--hours', type=int, default=24, help='Time frame in hours')
    
    return parser


async def main():
    """Main CLI function"""
    
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level)
    
    # Create CLI instance
    cli = MultiChainCLI()
    
    # Initialize
    if not await cli.initialize(args.config):
        return 1
    
    # Execute command
    try:
        success = False
        
        if args.command == 'status':
            success = await cli.cmd_status(args)
        elif args.command == 'sync':
            success = await cli.cmd_sync(args)
        elif args.command == 'monitor':
            success = await cli.cmd_monitor(args)
        elif args.command == 'analytics':
            success = await cli.cmd_analytics(args)
        elif args.command == 'chain':
            success = await cli.cmd_chain(args)
        elif args.command == 'compare':
            success = await cli.cmd_compare(args)
        elif args.command == 'export':
            success = await cli.cmd_export(args)
        else:
            console.print(f"[red]❌ Unknown command: {args.command}[/red]")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        console.print("\n⚠️ Operation interrupted by user")
        return 0
    except Exception as e:
        if args.verbose:
            import traceback
            console.print(f"[red]❌ Error: {traceback.format_exc()}[/red]")
        else:
            console.print(f"[red]❌ Error: {e}[/red]")
        return 1
    finally:
        await cli.close_connections()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))