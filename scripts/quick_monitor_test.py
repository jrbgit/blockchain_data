#!/usr/bin/env python3
"""
Quick test of real-time monitor with analytics integration
Runs for 15 seconds then stops
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / \"src\"))

from core.config import Config
from processors.realtime_monitor import RealtimeMonitor
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

async def main():
    """Run a brief test of the real-time monitor with analytics."""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    console.print(Panel(
        Text("🔄 Quick Analytics Integration Test - 15 Second Run", style="bold green"),
        border_style="green"
    ))
    
    # Load configuration
    config = Config()
    console.print(f"📊 Analytics enabled: {config.is_analytics_enabled()}")
    
    # Create monitor
    monitor = RealtimeMonitor(config)
    
    try:
        # Initialize
        console.print("🔌 Initializing monitor...")
        if not await monitor.initialize():
            console.print("❌ Failed to initialize")
            return False
            
        console.print("✅ Monitor initialized successfully")
        console.print(f"   Analytics enabled: {monitor.stats.get('analytics_enabled', False)}")
        console.print(f"   Starting from block: {monitor.last_processed_block}")
        console.print(f"   Latest network block: {monitor.latest_network_block}")
        
        # Start monitoring for 15 seconds
        console.print("🚀 Starting 15-second monitoring test...")
        
        # Set up timeout
        async def timeout_handler():
            await asyncio.sleep(15)
            console.print("⏰ Timeout reached, stopping monitor...")
            await monitor.stop_monitoring()
        
        # Start timeout task
        timeout_task = asyncio.create_task(timeout_handler())
        
        # Start monitoring (this will run until stopped)
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        # Wait for either to complete
        done, pending = await asyncio.wait(
            [monitor_task, timeout_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel any pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Show final results
        console.print("\n📊 Final Results:")
        stats = monitor.stats
        console.print(f"   Blocks processed: {stats.get('blocks_processed', 0)}")
        console.print(f"   Transactions processed: {stats.get('transactions_processed', 0)}")
        console.print(f"   Events processed: {stats.get('events_processed', 0)}")
        console.print(f"   Analytics events: {stats.get('total_analytics_events', 0)}")
        console.print(f"   Token transfers: {stats.get('token_transfers_found', 0)}")
        console.print(f"   DEX swaps: {stats.get('dex_swaps_found', 0)}")
        console.print(f"   Analytics timeouts: {stats.get('analytics_timeouts', 0)}")
        if stats.get('analytics_processing_time', 0) > 0:
            console.print(f"   Avg analytics time: {stats.get('analytics_processing_time', 0):.3f}s")
        
        console.print("\n✅ Test completed successfully!")
        return True
        
    except KeyboardInterrupt:
        console.print("\n⚠️ Test interrupted by user")
        return True
    except Exception as e:
        console.print(f"\n❌ Test failed: {e}")
        return False
    finally:
        try:
            await monitor.stop_monitoring()
        except:
            pass

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        sys.exit(0)
