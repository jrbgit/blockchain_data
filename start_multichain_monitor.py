#!/usr/bin/env python3
"""
Multi-Chain Blockchain Monitor Startup Script

Starts the enhanced multi-chain monitoring dashboard with different display modes.
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import Config
from src.processors.multichain_monitor import (
    MultiChainMonitor,
    run_multichain_overview,
    run_multichain_detailed, 
    run_multichain_analytics,
    run_chain_comparison
)
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/multichain_monitor.log')
        ]
    )

def print_banner():
    """Print startup banner"""
    console.print(Panel(
        Text("🔗 Multi-Chain Blockchain Monitor", style="bold blue"),
        subtitle="Enhanced monitoring for GLQ, Ethereum, Polygon, Base, Avalanche, and BSC",
        border_style="blue"
    ))

async def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(
        description="Multi-Chain Blockchain Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Display Modes:
  overview     - Table overview of all chains (default)
  detailed     - Individual panels for each chain 
  analytics    - Cross-chain analytics and rankings
  comparison   - Side-by-side performance comparison

Examples:
  python start_multichain_monitor.py
  python start_multichain_monitor.py --mode analytics
  python start_multichain_monitor.py --mode comparison --chains ethereum polygon
  python start_multichain_monitor.py --mode detailed --chains glq ethereum --verbose
        """
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['overview', 'detailed', 'analytics', 'comparison'],
        default='overview',
        help='Display mode (default: overview)'
    )
    
    parser.add_argument(
        '--chains', '-c',
        nargs='*',
        help='Specific chains to monitor (default: all connected chains)',
        metavar='CHAIN'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=3,
        help='Polling interval in seconds (default: 3)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Print banner
    print_banner()
    
    # Load configuration
    try:
        config = Config()
        if args.interval:
            # Set monitoring configuration using the get method
            if not hasattr(config, 'monitoring'):
                config.monitoring = {}
            config.monitoring['poll_interval'] = args.interval
            
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        return 1
    
    console.print(f"🚀 Starting monitor in [bold cyan]{args.mode}[/bold cyan] mode...")
    
    if args.chains:
        console.print(f"📍 Monitoring specific chains: [yellow]{', '.join(args.chains)}[/yellow]")
    else:
        console.print("📍 Monitoring all available chains")
    
    console.print(f"⏱️  Polling interval: [green]{args.interval}s[/green]")
    console.print()
    
    # Start appropriate monitoring mode
    try:
        if args.mode == "overview":
            await run_multichain_overview(config, args.chains)
        elif args.mode == "detailed":
            await run_multichain_detailed(config, args.chains)
        elif args.mode == "analytics":
            await run_multichain_analytics(config)
        elif args.mode == "comparison":
            await run_chain_comparison(config)
            
    except KeyboardInterrupt:
        console.print("\n⚠️  Monitoring interrupted by user")
        return 0
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)