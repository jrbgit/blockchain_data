#!/usr/bin/env python3
"""
Multi-Chain Blockchain Analytics Platform
Main entry point for all analytics operations across multiple blockchain networks.
"""
import sys
import os
import asyncio
import argparse
from pathlib import Path
from typing import List, Optional

# Add scripts and src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))

from src.core.config import Config
from src.processors.multichain_processor import MultiChainProcessor


async def run_multichain_sync(chains: Optional[List[str]] = None, max_blocks: Optional[int] = None):
    """Run multi-chain historical synchronization"""
    try:
        config = Config()
        print(f"Starting multi-chain historical sync for {len(config.chains)} configured chains...")
        
        # Use context manager to ensure proper connection and cleanup
        async with MultiChainProcessor(config) as processor:
            success = await processor.process_historical_data(
                chains=chains,
                max_blocks=max_blocks
            )
        
        if success:
            print("Multi-chain synchronization completed successfully!")
        else:
            print("Multi-chain synchronization failed!")
            return False
        
    except Exception as e:
        print(f"Error during multi-chain sync: {e}")
        return False
    
    return True

async def run_multichain_monitor(chains: Optional[List[str]] = None, interval: int = 2):
    """Run multi-chain real-time monitoring"""
    try:
        config = Config()
        print(f"Starting multi-chain real-time monitoring...")
        
        # Use context manager to ensure proper connection and cleanup
        async with MultiChainProcessor(config) as processor:
            await processor.process_realtime(
                chains=chains,
                polling_interval=interval
            )
        
    except KeyboardInterrupt:
        print("\nMulti-chain monitoring stopped by user")
    except Exception as e:
        print(f"Error during multi-chain monitoring: {e}")

async def run_multichain_test():
    """Run multi-chain connectivity tests"""
    print("Running multi-chain connectivity tests...")
    os.system("python tests/test_multichain_simple.py")

def main():
    parser = argparse.ArgumentParser(
        description='Multi-Chain Blockchain Analytics Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  sync         Run blockchain synchronization (multi-chain or single chain)
  monitor      Start real-time blockchain monitoring (multi-chain or single chain)
  service      Start monitoring service with health checks
  test         Run connectivity and setup tests
  multichain   Multi-chain specific operations
  legacy       Run legacy GLQ-only commands
  
Examples:
  python glq_analytics.py sync                           # Sync all connected chains
  python glq_analytics.py sync --chains ethereum,polygon # Sync specific chains
  python glq_analytics.py sync --max-blocks 1000         # Limit blocks per chain
  python glq_analytics.py monitor                        # Monitor all chains
  python glq_analytics.py monitor --chains glq           # Monitor only GLQ chain
  python glq_analytics.py test                           # Test all connections
  python glq_analytics.py legacy sync                    # Run original GLQ sync
        """
    )
    
    parser.add_argument(
        'command',
        choices=['sync', 'monitor', 'service', 'test', 'legacy'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'subcommand',
        nargs='?',
        help='Subcommand for legacy operations'
    )
    
    parser.add_argument(
        '--chains',
        help='Comma-separated list of chain IDs to process (e.g., ethereum,polygon,glq)'
    )
    
    parser.add_argument(
        '--max-blocks',
        type=int,
        help='Maximum number of blocks to process per chain'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=2,
        help='Polling interval in seconds for real-time monitoring (default: 2)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to config file (default: config/config.yaml)',
        default='config/config.yaml'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        os.environ['DEBUG_MODE'] = 'true'
    
    # Parse chain list if provided
    chains = None
    if args.chains:
        chains = [chain.strip() for chain in args.chains.split(',')]
    
    print("🚀 Multi-Chain Blockchain Analytics Platform")
    print("=" * 50)
    
    try:
        if args.command == 'sync':
            print("Starting multi-chain blockchain synchronization...")
            if chains:
                print(f"Target chains: {', '.join(chains)}")
            if args.max_blocks:
                print(f"Max blocks per chain: {args.max_blocks:,}")
            
            success = asyncio.run(run_multichain_sync(
                chains=chains,
                max_blocks=args.max_blocks
            ))
            
            if not success:
                sys.exit(1)
                
        elif args.command == 'monitor':
            print("Starting multi-chain real-time monitoring...")
            if chains:
                print(f"Monitoring chains: {', '.join(chains)}")
            print(f"Polling interval: {args.interval} seconds")
            
            asyncio.run(run_multichain_monitor(
                chains=chains,
                interval=args.interval
            ))
            
        elif args.command == 'service':
            print("Starting monitoring service...")
            os.system(f"python scripts/start_monitor_service.py")
            
        elif args.command == 'test':
            print("Running multi-chain connectivity tests...")
            asyncio.run(run_multichain_test())
            
        elif args.command == 'legacy':
            if not args.subcommand:
                print("Legacy command requires a subcommand: sync, monitor, service, or test")
                sys.exit(1)
                
            print(f"Running legacy GLQ-only command: {args.subcommand}")
            
            if args.subcommand == 'sync':
                os.system(f"python scripts/full_sync_with_analytics.py")
            elif args.subcommand == 'monitor':
                os.system(f"python scripts/start_realtime_monitor.py")
            elif args.subcommand == 'service':
                os.system(f"python scripts/start_monitor_service.py")
            elif args.subcommand == 'test':
                os.system(f"python tests/test_sync_setup.py")
            else:
                print(f"Unknown legacy subcommand: {args.subcommand}")
                sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()