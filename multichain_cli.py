#!/usr/bin/env python3
"""
Multi-Chain CLI - Simplified Working Version

This is a working version of the multi-chain CLI that avoids import issues.
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add src to path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

# Import with fallback
try:
    from core.config import Config
    from core.multichain_client import MultiChainClient
    from core.multichain_influxdb_client import MultiChainInfluxDB
    IMPORTS_OK = True
except ImportError as e:
    console.print(f"[red]Import error: {e}[/red]")
    IMPORTS_OK = False


async def cmd_status():
    """Show multi-chain system status"""
    if not IMPORTS_OK:
        console.print("[red]❌ Cannot load required modules. Check your installation.[/red]")
        return False
    
    console.print(Panel(
        Text("🔗 Multi-Chain System Status", style="bold blue"),
        border_style="blue"
    ))
    
    try:
        config = Config()
        console.print("✅ Configuration loaded successfully")
        
        # Show configured chains
        table = Table(title="Configured Chains", expand=True)
        table.add_column("Chain ID", style="cyan", width=15)
        table.add_column("Name", style="green", width=20) 
        table.add_column("Provider", width=10)
        table.add_column("Enabled", justify="center", width=10)
        
        for chain_id, chain_config in config.chains.items():
            enabled = "✅ Yes" if chain_config.get('enabled', False) else "❌ No"
            table.add_row(
                chain_id,
                chain_config.get('name', 'Unknown'),
                chain_config.get('provider', 'unknown'),
                enabled
            )
        
        console.print(table)
        console.print(f"\n📊 Total chains configured: {len(config.chains)}")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return False


async def cmd_test_connections():
    """Test connections to all chains"""
    if not IMPORTS_OK:
        console.print("[red]❌ Cannot load required modules. Check your installation.[/red]")
        return False
    
    console.print(Panel(
        Text("🧪 Testing Chain Connections", style="bold yellow"),
        border_style="yellow"
    ))
    
    try:
        config = Config()
        multichain_client = MultiChainClient(config)
        
        console.print("🔌 Connecting to chains...")
        await multichain_client.connect()
        
        connected_chains = multichain_client.get_connected_chains()
        console.print(f"✅ Connected to {len(connected_chains)} chains")
        
        # Test each chain
        table = Table(title="Connection Test Results", expand=True)
        table.add_column("Chain", style="cyan", width=20)
        table.add_column("Status", justify="center", width=15)
        table.add_column("Latest Block", justify="right", width=15)
        table.add_column("Chain ID", justify="right", width=10)
        
        for chain_id in connected_chains:
            try:
                latest_block = await multichain_client.get_latest_block_number(chain_id)
                chain_info = await multichain_client.get_chain_info(chain_id)
                
                chain_name = config.chains[chain_id]['name']
                status = "[green]●[/green] Connected"
                block_display = f"{latest_block:,}" if latest_block else "N/A"
                actual_chain_id = chain_info.get('chain_id', 'Unknown')
                
            except Exception as e:
                chain_name = config.chains.get(chain_id, {}).get('name', chain_id)
                status = "[red]●[/red] Error"
                block_display = str(e)[:20] + "..."
                actual_chain_id = "Unknown"
            
            table.add_row(chain_name, status, block_display, str(actual_chain_id))
        
        console.print(table)
        
        await multichain_client.close()
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Connection test failed: {e}[/red]")
        return False


async def cmd_info():
    """Show system information"""
    console.print(Panel(
        Text("ℹ️ Multi-Chain Analytics System Information", style="bold cyan"),
        border_style="cyan"
    ))
    
    info_text = Text()
    info_text.append("🔗 Multi-Chain Blockchain Analytics Platform\n", style="bold blue")
    info_text.append("📊 Version: 2.0 (Multi-Chain)\n", style="green")
    info_text.append("🌐 Supported Networks:\n", style="yellow")
    info_text.append("  • GLQ Chain (GraphLinq Chain) - Local RPC\n", style="dim")
    info_text.append("  • Ethereum Mainnet - via Infura\n", style="dim")
    info_text.append("  • Polygon Mainnet - via Infura\n", style="dim")
    info_text.append("  • Base Mainnet - via Infura\n", style="dim")
    info_text.append("  • Avalanche C-Chain - via Infura\n", style="dim")
    info_text.append("  • BNB Smart Chain - via Infura\n", style="dim")
    info_text.append("\n🚀 Available Features:\n", style="yellow")
    info_text.append("  • Real-time multi-chain monitoring\n", style="dim")
    info_text.append("  • Cross-chain analytics and comparisons\n", style="dim")
    info_text.append("  • DeFi metrics and bridge activity tracking\n", style="dim")
    info_text.append("  • Professional report generation\n", style="dim")
    info_text.append("  • Command-line interface for all operations\n", style="dim")
    
    console.print(Panel(info_text, title="System Information", border_style="cyan"))


def create_parser():
    """Create argument parser"""
    
    parser = argparse.ArgumentParser(
        description="Multi-Chain Blockchain Analytics CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python multichain_cli.py status          # Show system configuration
  python multichain_cli.py test            # Test chain connections  
  python multichain_cli.py info            # Show system information
  python multichain_cli.py monitor         # Start monitoring dashboard
  python multichain_cli.py help            # Show detailed help

For advanced operations, use the full CLI:
  python src/cli/multichain_cli.py --help
  
For monitoring dashboard:
  python start_multichain_monitor.py --help
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=['status', 'test', 'info', 'monitor', 'help'],
        default='help',
        help='Command to execute'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser


async def main():
    """Main function"""
    
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == 'help':
        parser.print_help()
        console.print("\n" + "="*60)
        console.print("🔗 MULTI-CHAIN BLOCKCHAIN ANALYTICS SYSTEM")
        console.print("="*60)
        console.print("This system provides comprehensive analytics for multiple blockchain networks.")
        console.print("\n📖 For detailed usage instructions, see: MULTICHAIN_USAGE.md")
        console.print("🚀 Quick start: python multichain_cli.py status")
        console.print("📊 Monitoring: python start_multichain_monitor.py")
        return 0
    
    # Execute command
    try:
        success = False
        
        if args.command == 'status':
            success = await cmd_status()
        elif args.command == 'test':
            success = await cmd_test_connections() 
        elif args.command == 'info':
            await cmd_info()
            success = True
        elif args.command == 'monitor':
            console.print("🚀 Starting monitoring dashboard...")
            console.print("Use: python start_multichain_monitor.py")
            success = True
        
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


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))