#!/usr/bin/env python3
"""
Clear Analytics Field Type Conflicts

This script clears analytics measurements that have field type conflicts
to allow fresh data to be written with consistent types.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / \"src\"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Clear analytics data with field type conflicts."""
    
    config = Config()
    
    if not config.influxdb_token:
        logger.error("No InfluxDB token configured. Please check your config.")
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
        
        # Clear conflicting analytics data
        logger.info("🧹 Clearing analytics measurements with field type conflicts...")
        await db_client.clear_analytics_data()
        
        logger.info("✅ Successfully cleared conflicting analytics data")
        logger.info("\n📊 The following measurements have been cleared:")
        logger.info("  • token_transfers")
        logger.info("  • dex_swaps") 
        logger.info("  • dex_liquidity")
        logger.info("  • defi_events")
        
        logger.info("\n🚀 You can now restart reset_and_sync.py to continue with consistent field types.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    finally:
        if 'db_client' in locals():
            db_client.close()

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n👋 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
