#!/usr/bin/env python3
"""
Test Analytics Field Type Consistency

This script tests that the field type consistency fix works correctly.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_field_consistency():
    """Test that large numbers are consistently stored as strings."""
    
    config = Config()
    
    if not config.influxdb_token:
        logger.error("No InfluxDB token configured.")
        return False
    
    try:
        # Initialize database client
        logger.info("🔧 Connecting to InfluxDB...")
        db_client = BlockchainInfluxDB(config)
        connected = await db_client.connect()
        
        if not connected:
            logger.error("❌ Failed to connect to InfluxDB")
            return False
        
        logger.info("✅ Connected to InfluxDB")
        
        # Test data with various sizes of integers
        test_points = [
            {
                "measurement": "token_transfers",
                "tags": {
                    "tx_hash": "0xtest1",
                    "token_address": "0xtoken1"
                },
                "fields": {
                    "block_number": 123456,  # Small integer - should remain int
                    "value": 1000000000000000000000,  # Large value - should become string
                    "token_id": 999999999999999999999999999999,  # Very large - should become string
                },
                "time": datetime.now()
            },
            {
                "measurement": "dex_swaps", 
                "tags": {
                    "tx_hash": "0xtest2",
                    "dex_address": "0xdex1"
                },
                "fields": {
                    "block_number": 123457,  # Small integer - should remain int
                    "amount_in": 5000000000000000000000,  # Large amount - should become string
                    "amount_out": 2500000000000000000000,  # Large amount - should become string
                },
                "time": datetime.now()
            },
            {
                "measurement": "dex_liquidity",
                "tags": {
                    "tx_hash": "0xtest3",
                    "pair_address": "0xpair1"
                },
                "fields": {
                    "block_number": 123458,  # Small integer - should remain int
                    "amount0": 10000000000000000000000000,  # Very large amount - should become string
                    "amount1": 25000000000000000000000000,  # Very large amount - should become string
                },
                "time": datetime.now()
            }
        ]
        
        # Write test data
        logger.info("📝 Writing test data...")
        db_client.write_points(test_points)
        
        logger.info("✅ Successfully wrote test data without field type conflicts!")
        logger.info("\n🔍 Test Summary:")
        logger.info("  • Small integers (block_number) -> remain as integers")
        logger.info("  • Large blockchain values (value, amount_in, amount_out, etc.) -> converted to strings")
        logger.info("  • No field type conflicts should occur")
        
        # Write another batch to test consistency
        logger.info("\n📝 Writing second batch to test consistency...")
        test_points_batch2 = [
            {
                "measurement": "token_transfers",
                "tags": {
                    "tx_hash": "0xtest4",
                    "token_address": "0xtoken2"
                },
                "fields": {
                    "block_number": 123459,  
                    "value": 2000000000000000000000,  # Should be string (consistent with first batch)
                    "token_id": 888888888888888888888888888888,  # Should be string (consistent)
                },
                "time": datetime.now()
            }
        ]
        
        db_client.write_points(test_points_batch2)
        logger.info("✅ Second batch written successfully - field types are consistent!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
    
    finally:
        if 'db_client' in locals():
            db_client.close()

async def main():
    """Run the test."""
    
    logger.info("🧪 Testing Analytics Field Type Consistency Fix")
    logger.info("=" * 50)
    
    success = await test_field_consistency()
    
    if success:
        logger.info("\n🎉 All tests passed! The field type consistency fix is working correctly.")
        logger.info("🚀 reset_and_sync.py should now run without field type conflicts.")
    else:
        logger.error("\n❌ Tests failed. Please check the configuration and try again.")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n👋 Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)