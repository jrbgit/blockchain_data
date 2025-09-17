#!/usr/bin/env python3
"""
Reset and Full Sync Script
Clears all stored blockchain data and starts a fresh sync from block 1
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB
from core.blockchain_client import BlockchainClient
from processors.historical_processor import HistoricalProcessor
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress

console = Console()
logger = logging.getLogger(__name__)

class DataResetAndSync:
    """Handle data clearing and fresh sync."""
    
    def __init__(self):
        self.config = Config()
        self.db_client = None
        self.blockchain_client = None
        
    async def initialize(self):
        """Initialize connections."""
        console.print(Panel(
            Text("🔧 Initializing connections...", style="bold cyan"),
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
            console.print(f"   Chain ID: {self.blockchain_client.chain_id}")
            
            # Initialize database client
            if self.config.influxdb_token:
                self.db_client = BlockchainInfluxDB(self.config)
                db_connected = await self.db_client.connect()
                
                if not db_connected:
                    console.print("❌ Failed to connect to InfluxDB")
                    return False
                    
                console.print("✅ Connected to InfluxDB")
                console.print(f"   URL: {self.config.influxdb_url}")
                console.print(f"   Bucket: {self.config.influxdb_bucket}")
            else:
                console.print("❌ No InfluxDB token configured")
                return False
                
            return True
            
        except Exception as e:
            console.print(f"❌ Initialization failed: {e}")
            logger.error(f"Initialization error: {e}", exc_info=True)
            return False
    
    async def clear_existing_data(self):
        """Clear all existing blockchain data."""
        console.print(Panel(
            Text("🗑️ Clearing Existing Data", style="bold red"),
            border_style="red"
        ))
        
        if not self.db_client:
            console.print("❌ Database client not available")
            return False
        
        try:
            # Get current data stats before clearing
            latest_block = self.db_client.query_latest_block()
            
            if latest_block is not None:
                console.print(f"📊 Current data goes up to block: {latest_block:,}")
                
                # Confirm deletion
                confirm = console.input("\n⚠️  [bold yellow]Are you sure you want to delete ALL blockchain data? [y/N]: [/bold yellow]")
                
                if confirm.lower() != 'y':
                    console.print("❌ Data clearing cancelled by user")
                    return False
                
                console.print("🗑️ Clearing all data from InfluxDB...")
                
                # Use the clear_all_data method
                await self.db_client.clear_all_data()
                console.print("✅ Data clearing completed")
            else:
                console.print("ℹ️ No existing data found - starting fresh")
                
            return True
            
        except Exception as e:
            console.print(f"❌ Error clearing data: {e}")
            logger.error(f"Data clearing error: {e}", exc_info=True)
            return False
    
    async def get_chain_info(self):
        """Get information about the blockchain."""
        console.print(Panel(
            Text("🔍 Analyzing Blockchain", style="bold blue"),
            border_style="blue"
        ))
        
        try:
            latest_block = await self.blockchain_client.get_latest_block_number()
            console.print(f"📊 Latest block on network: {latest_block:,}")
            
            # Get first few blocks to check data availability
            console.print("🔍 Checking early blocks...")
            
            early_blocks = []
            for block_num in [1, 2, 3, 100, 1000]:
                try:
                    block_data = await self.blockchain_client.get_block(block_num, include_transactions=True)
                    if block_data:
                        tx_count = len(block_data.get('transactions', []))
                        early_blocks.append((block_num, tx_count))
                        console.print(f"   Block {block_num}: ✅ Available ({tx_count} transactions)")
                    else:
                        console.print(f"   Block {block_num}: ❌ Not available")
                except Exception as e:
                    console.print(f"   Block {block_num}: ❌ Error: {e}")
            
            if early_blocks:
                console.print(f"✅ Blockchain data accessible from block 1")
                console.print(f"📈 Total blocks to sync: {latest_block:,}")
                
                # Estimate sync time
                estimated_hours = latest_block / 1000  # rough estimate
                console.print(f"⏱️ Estimated sync time: ~{estimated_hours:.1f} hours")
                
                return latest_block
            else:
                console.print("❌ Unable to access early blockchain data")
                return None
                
        except Exception as e:
            console.print(f"❌ Error analyzing blockchain: {e}")
            return None
    
    async def start_full_sync(self, target_block):
        """Start the full historical sync."""
        console.print(Panel(
            Text("🚀 Starting Full Historical Sync", style="bold green"),
            border_style="green"
        ))
        
        try:
            # Update configuration for full sync
            temp_config = Config()
            temp_config.update('processing.start_block', 1)
            temp_config.update('processing.end_block', target_block)
            temp_config.update('processing.batch_size', 100)  # Smaller batches for stability
            temp_config.update('processing.max_workers', 4)   # Moderate parallelism
            
            console.print(f"🎯 Sync configuration:")
            console.print(f"   Start block: 1")
            console.print(f"   End block: {target_block:,}")
            console.print(f"   Batch size: 100 blocks")
            console.print(f"   Workers: 4")
            console.print(f"   Analytics enabled: {temp_config.is_analytics_enabled()}")
            
            # Confirm start
            confirm = console.input("\n🚀 [bold green]Start full sync now? [Y/n]: [/bold green]")
            
            if confirm.lower() in ['', 'y', 'yes']:
                # Create historical processor
                processor = HistoricalProcessor(temp_config)
                
                console.print("🔄 Starting historical sync with analytics...")
                console.print("   This will take several hours - you can monitor progress in another terminal")
                console.print("   Use Ctrl+C to stop gracefully")
                
                # Start the sync
                success = await processor.process_blocks()
                
                if success:
                    console.print("✅ Full sync completed successfully!")
                    return True
                else:
                    console.print("❌ Full sync failed")
                    return False
            else:
                console.print("❌ Full sync cancelled by user")
                return False
                
        except KeyboardInterrupt:
            console.print("\n⚠️ Sync interrupted by user")
            return False
        except Exception as e:
            console.print(f"❌ Sync error: {e}")
            logger.error(f"Full sync error: {e}", exc_info=True)
            return False
    
    async def cleanup(self):
        """Cleanup connections."""
        if self.blockchain_client:
            self.blockchain_client.close()
        if self.db_client:
            self.db_client.close()

async def main():
    """Main function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/full_sync.log')
        ]
    )
    
    console.print(Panel(
        Text("🔄 GLQ Chain Full Sync - Data Reset and Resync", style="bold white"),
        subtitle="This will clear all existing data and sync from block 1",
        border_style="white"
    ))
    
    reset_sync = DataResetAndSync()
    
    try:
        # Initialize
        if not await reset_sync.initialize():
            console.print("❌ Initialization failed")
            return False
        
        # Clear existing data
        if not await reset_sync.clear_existing_data():
            console.print("❌ Data clearing failed")
            return False
        
        # Analyze blockchain
        target_block = await reset_sync.get_chain_info()
        if not target_block:
            console.print("❌ Blockchain analysis failed")
            return False
        
        # Start full sync
        success = await reset_sync.start_full_sync(target_block)
        
        if success:
            console.print(Panel(
                Text("🎉 Full Sync Completed!", style="bold green"),
                subtitle="Your GLQ Chain data is now fully synced with analytics",
                border_style="green"
            ))
        
        return success
        
    except KeyboardInterrupt:
        console.print("\n⚠️ Process interrupted by user")
        return False
    except Exception as e:
        console.print(f"❌ Process failed: {e}")
        logger.error(f"Main process error: {e}", exc_info=True)
        return False
    finally:
        await reset_sync.cleanup()

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        sys.exit(0)