#!/usr/bin/env python3
"""
GLQ Chain Blockchain Analytics Platform
Main entry point for all analytics operations.
"""
import sys
import os
import argparse
from pathlib import Path

# Add scripts and src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))


def main():
    parser = argparse.ArgumentParser(
        description='GLQ Chain Blockchain Analytics Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  sync         Run full blockchain synchronization with analytics
  monitor      Start real-time blockchain monitoring
  service      Start monitoring service with health checks
  test         Run connectivity and setup tests
  
Examples:
  python glq_analytics.py sync        # Full blockchain sync
  python glq_analytics.py monitor     # Real-time monitoring
  python glq_analytics.py test        # Test connections
        """
    )
    
    parser.add_argument(
        'command',
        choices=['sync', 'monitor', 'service', 'test'],
        help='Command to execute'
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
    
    print("🚀 GLQ Chain Blockchain Analytics Platform")
    print("=" * 50)
    
    try:
        if args.command == 'sync':
            print("Starting full blockchain synchronization with analytics...")
            os.system(f"python scripts/full_sync_with_analytics.py")
            
        elif args.command == 'monitor':
            print("Starting real-time blockchain monitoring...")
            os.system(f"python scripts/start_realtime_monitor.py")
            
        elif args.command == 'service':
            print("Starting monitoring service...")
            os.system(f"python scripts/start_monitor_service.py")
            
        elif args.command == 'test':
            print("Running connectivity and setup tests...")
            os.system(f"python tests/test_sync_setup.py")
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()