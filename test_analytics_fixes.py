#!/usr/bin/env python3
"""
Test Analytics Fixes

Test script to verify that the integer overflow and write_points issues have been resolved.
Tests specific block numbers that were failing in the logs.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.blockchain_client import BlockchainClient
from core.influxdb_client import BlockchainInfluxDB
from analytics.advanced_analytics import AdvancedAnalytics
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

console = Console()
logger = logging.getLogger(__name__)


class AnalyticsFixer:
    """Test analytics fixes with problematic blocks."""
    
    # Block numbers from the logs that were failing
    PROBLEMATIC_BLOCKS = [
        3113574,  # First integer overflow error
        3113578,  # Additional integer overflow
        3113581,  # Additional integer overflow  
        3113584,  # Additional integer overflow
        3115216,  # First write_points error
        3115227,  # Additional write_points error
        3118324,  # More failures
        3119075,  # More failures
        3119084,  # More failures
        3120096,  # More failures
    ]
    
    def __init__(self):
        self.config = Config()
        self.blockchain_client = None
        self.db_client = None
        self.analytics = None
        
    async def initialize(self):
        """Initialize connections."""
        console.print(Panel(
            "🔧 Initializing Analytics Fix Test",
            border_style="cyan"
        ))
        
        try:
            # Initialize blockchain client
            self.blockchain_client = BlockchainClient(self.config)
            blockchain_connected = await self.blockchain_client.connect()
            
            if not blockchain_connected:
                console.print("❌ Failed to connect to blockchain")
                return False
            
            console.print("✅ Connected to GLQ Chain")
            
            # Initialize database client
            if self.config.influxdb_token:
                self.db_client = BlockchainInfluxDB(self.config)
                db_connected = await self.db_client.connect()
                
                if not db_connected:
                    console.print("❌ Failed to connect to InfluxDB")
                    return False
                    
                console.print("✅ Connected to InfluxDB")
            else:
                console.print("❌ No InfluxDB token configured")
                return False
            
            # Initialize analytics
            self.analytics = AdvancedAnalytics(
                blockchain_client=self.blockchain_client,
                db_client=self.db_client,
                config=self.config
            )
            console.print("✅ Advanced analytics initialized")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Initialization failed: {e}")
            return False
    
    async def test_specific_block(self, block_number: int) -> dict:
        """Test analytics processing for a specific block."""
        console.print(f"🔍 Testing block {block_number:,}")
        
        result = {
            'block_number': block_number,
            'success': False,
            'error': None,
            'token_transfers': 0,
            'dex_swaps': 0,
            'liquidity_events': 0,
            'defi_events': 0,
            'total_events': 0,
            'transactions_processed': 0
        }
        
        try:
            # Get block data with transactions
            block_data = await self.blockchain_client.get_block(
                block_number, include_transactions=True
            )
            
            if not block_data:
                result['error'] = "Block data not found"
                return result
            
            # Create timestamp
            timestamp = datetime.fromtimestamp(
                int(block_data['timestamp'], 16),
                tz=timezone.utc
            )
            
            # Process block with analytics
            analytics_result = await self.analytics.analyze_block(block_data, timestamp)
            
            # Update results
            result['success'] = True
            result['token_transfers'] = analytics_result.get('token_transfers', 0)
            result['dex_swaps'] = analytics_result.get('dex_swaps', 0)
            result['liquidity_events'] = analytics_result.get('liquidity_events', 0)
            result['defi_events'] = (
                analytics_result.get('lending_events', 0) + 
                analytics_result.get('staking_events', 0) + 
                analytics_result.get('yield_events', 0)
            )
            result['total_events'] = analytics_result.get('total_events_found', 0)
            result['transactions_processed'] = analytics_result.get('transactions_processed', 0)
            
            if result['total_events'] > 0:
                console.print(f"  ✅ Found {result['total_events']} events")
                console.print(f"     • Token transfers: {result['token_transfers']}")
                console.print(f"     • DEX swaps: {result['dex_swaps']}")
                console.print(f"     • Liquidity events: {result['liquidity_events']}")
                console.print(f"     • DeFi events: {result['defi_events']}")
            else:
                console.print(f"  ℹ️ No events found (expected for some blocks)")
            
        except Exception as e:
            result['error'] = str(e)
            console.print(f"  ❌ Error: {e}")
            logger.exception(f"Error testing block {block_number}")
            
        return result
    
    async def test_all_problematic_blocks(self):
        """Test all problematic blocks from the logs."""
        console.print(Panel(
            "🧪 Testing Problematic Blocks from Error Logs",
            border_style="yellow"
        ))
        
        results = []
        successful = 0
        failed = 0
        total_events = 0
        
        with Progress(console=console) as progress:
            task = progress.add_task(
                "Testing blocks...", 
                total=len(self.PROBLEMATIC_BLOCKS)
            )
            
            for block_number in self.PROBLEMATIC_BLOCKS:
                result = await self.test_specific_block(block_number)
                results.append(result)
                
                if result['success']:
                    successful += 1
                    total_events += result['total_events']
                else:
                    failed += 1
                
                progress.advance(task)
                
        return results, successful, failed, total_events
    
    async def test_large_integer_handling(self):
        """Test that large integers are handled correctly."""
        console.print(Panel(
            "🔢 Testing Large Integer Handling",
            border_style="green"
        ))
        
        try:
            # Test writing a point with very large integers directly
            large_value = 9350000000000000000000  # Value from error logs
            
            test_points = [{
                "measurement": "token_transfers",
                "tags": {
                    "tx_hash": "0xtest123",
                    "token_address": "0xeb567ec41738c2bab2599a1070fc5b727721b3b6",
                    "token_type": "ERC20",
                    "from_address": "0x0000000000000000000000000000000000000000",
                    "to_address": "0x4632babf430e797aedec7392a31dcd63c2b0c25c"
                },
                "fields": {
                    "block_number": 3113574,
                    "log_index": 0,
                    "token_id": 0,
                    "value": large_value  # This was causing the overflow
                },
                "time": datetime.now(timezone.utc)
            }]
            
            # This should now work without integer overflow
            self.db_client.write_points(test_points)
            console.print("✅ Large integer handling test passed")
            return True
            
        except Exception as e:
            console.print(f"❌ Large integer test failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up connections."""
        if self.blockchain_client:
            self.blockchain_client.close()
        if self.db_client:
            self.db_client.close()
    
    async def run_all_tests(self):
        """Run all tests."""
        console.print(Panel(
            "🚀 Analytics Fixes Verification Test Suite",
            subtitle="Testing fixes for integer overflow and write_points errors",
            border_style="blue"
        ))
        
        try:
            # Initialize
            if not await self.initialize():
                console.print("❌ Test initialization failed")
                return False
            
            # Test large integer handling
            large_int_success = await self.test_large_integer_handling()
            
            # Test problematic blocks
            results, successful, failed, total_events = await self.test_all_problematic_blocks()
            
            # Print summary
            console.print(Panel(
                f"📊 Test Results Summary",
                border_style="green" if failed == 0 else "red"
            ))
            
            console.print(f"Large integer test: {'✅ PASSED' if large_int_success else '❌ FAILED'}")
            console.print(f"Blocks tested: {len(self.PROBLEMATIC_BLOCKS)}")
            console.print(f"Successful: {successful}")
            console.print(f"Failed: {failed}")
            console.print(f"Total events processed: {total_events}")
            
            if failed > 0:
                console.print("\n❌ Failed blocks:")
                for result in results:
                    if not result['success']:
                        console.print(f"  Block {result['block_number']}: {result['error']}")
            
            overall_success = large_int_success and failed == 0
            if overall_success:
                console.print("\n🎉 All tests passed! The analytics fixes are working correctly.")
            else:
                console.print("\n⚠️  Some tests failed. Please review the errors above.")
            
            return overall_success
            
        except Exception as e:
            console.print(f"❌ Test suite failed: {e}")
            logger.exception("Test suite error")
            return False
        
        finally:
            await self.cleanup()


async def main():
    """Main test function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/analytics_fix_test.log')
        ]
    )
    
    # Run tests
    tester = AnalyticsFixer()
    success = await tester.run_all_tests()
    
    return success


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n👋 Test interrupted by user")
        sys.exit(0)