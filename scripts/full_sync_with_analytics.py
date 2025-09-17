#!/usr/bin/env python3
"""
Full Blockchain Synchronization with Advanced Analytics
Runs historical processing with token, DEX, and DeFi analytics enabled.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import Config
from core.blockchain_client import BlockchainClient  
from core.influxdb_client import InfluxDBClient
from analytics.advanced_analytics import AdvancedAnalytics
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/full_sync.log', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class SimpleHistoricalProcessor:
    """Simple historical processor for analytics sync."""
    
    def __init__(self, config: Config):
        self.config = config
        self.blockchain_client = BlockchainClient(config)
        self.influx_client = InfluxDBClient(config)
        
        
class AnalyticsHistoricalProcessor(SimpleHistoricalProcessor):
    """Enhanced historical processor with advanced analytics."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        
        # Initialize analytics
        self.analytics = AdvancedAnalytics(
            blockchain_client=self.blockchain_client,
            db_client=self.influx_client, 
            config=config
        )
        
        # Analytics stats
        self.analytics_stats = {
            'total_token_transfers': 0,
            'total_dex_swaps': 0,
            'total_liquidity_events': 0,
            'total_lending_events': 0,
            'total_staking_events': 0,
            'total_yield_events': 0,
        }
        
    async def process_block_with_analytics(self, block_number: int) -> bool:
        """Process a single block with full analytics."""
        try:
            # Get block data with full transactions
            block_data = await self.blockchain_client.get_block(
                block_number, include_transactions=True
            )
            
            if not block_data:
                logger.warning(f"Could not fetch block {block_number}")
                return False
                
            # Create timestamp
            timestamp = datetime.fromtimestamp(
                int(block_data['timestamp'], 16), 
                tz=timezone.utc
            )
            
            # Process block with analytics
            block_results = await self.analytics.analyze_block(block_data, timestamp)
            
            # Store basic block data
            self.influx_client.write_block(block_data)
            
            # Process transactions
            if 'transactions' in block_data:
                for tx in block_data['transactions']:
                    if isinstance(tx, dict):
                        try:
                            # Get transaction receipt
                            receipt = await self.blockchain_client.get_transaction_receipt(tx['hash'])
                            if receipt:
                                # Store transaction
                                status = "success" if receipt.get('status') == '0x1' else "failed"
                                gas_used = int(receipt.get('gasUsed', '0x0'), 16)
                                self.influx_client.write_transaction(
                                    tx, block_number, status, gas_used
                                )
                                
                                # Store events/logs
                                if 'logs' in receipt:
                                    for log in receipt['logs']:
                                        self.influx_client.write_event(
                                            log, block_number, tx['hash']
                                        )
                                        
                        except Exception as e:
                            logger.error(f"Error processing tx {tx.get('hash', 'unknown')}: {e}")
            
            # Update analytics stats
            self.analytics_stats['total_token_transfers'] += block_results.get('token_transfers', 0)
            self.analytics_stats['total_dex_swaps'] += block_results.get('dex_swaps', 0)
            self.analytics_stats['total_liquidity_events'] += block_results.get('liquidity_events', 0)
            self.analytics_stats['total_lending_events'] += block_results.get('lending_events', 0)
            self.analytics_stats['total_staking_events'] += block_results.get('staking_events', 0)
            self.analytics_stats['total_yield_events'] += block_results.get('yield_events', 0)
            
            # Log progress with analytics
            if block_number % 100 == 0:
                logger.info(f"Processed block {block_number:,} with analytics:")
                logger.info(f"  - Transactions: {block_results.get('transactions_processed', 0)}")
                logger.info(f"  - Total events: {block_results.get('total_events_found', 0)}")
                logger.info(f"  - Token transfers: {block_results.get('token_transfers', 0)}")
                logger.info(f"  - DEX swaps: {block_results.get('dex_swaps', 0)}")
                logger.info(f"  - DeFi events: {block_results.get('lending_events', 0) + block_results.get('staking_events', 0) + block_results.get('yield_events', 0)}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing block {block_number} with analytics: {e}")
            return False
    
    async def sync_range_with_analytics(self, start_block: int, end_block: int):
        """Sync a range of blocks with analytics."""
        logger.info(f"Starting analytics sync from block {start_block:,} to {end_block:,}")
        
        processed = 0
        failed = 0
        
        for block_num in range(start_block, end_block + 1):
            try:
                success = await self.process_block_with_analytics(block_num)
                if success:
                    processed += 1
                else:
                    failed += 1
                    
                # Progress reporting
                if block_num % 1000 == 0:
                    completion = ((block_num - start_block + 1) / (end_block - start_block + 1)) * 100
                    logger.info(f"Progress: {completion:.1f}% ({block_num:,}/{end_block:,}) - "
                              f"Processed: {processed:,}, Failed: {failed:,}")
                    
                    # Analytics summary
                    logger.info(f"Analytics totals so far:")
                    for key, value in self.analytics_stats.items():
                        logger.info(f"  - {key.replace('_', ' ').title()}: {value:,}")
                        
            except KeyboardInterrupt:
                logger.info("Sync interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error at block {block_num}: {e}")
                failed += 1
                
        logger.info(f"Sync completed: {processed:,} blocks processed, {failed:,} failed")
        logger.info("Final analytics summary:")
        for key, value in self.analytics_stats.items():
            logger.info(f"  - {key.replace('_', ' ').title()}: {value:,}")


async def main():
    """Main sync function."""
    print("🚀 STARTING FULL BLOCKCHAIN SYNC WITH ADVANCED ANALYTICS")
    print("=" * 70)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    try:
        # Load configuration
        config = Config()
        logger.info("Configuration loaded")
        
        # Initialize processor with analytics
        processor = AnalyticsHistoricalProcessor(config)
        logger.info("Analytics processor initialized")
        
        # Get sync parameters
        latest_block_number = processor.blockchain_client.w3.eth.get_block('latest')['number']
        
        # Check if we should continue from where we left off
        last_synced = processor.influx_client.query_latest_block()
        
        if last_synced:
            start_block = last_synced + 1
            logger.info(f"Resuming sync from block {start_block:,} (last synced: {last_synced:,})")
        else:
            start_block = config.get('processing.start_block', 0)
            logger.info(f"Starting fresh sync from block {start_block:,}")
        
        # Determine end block
        end_block_config = config.get('processing.end_block', 'latest')
        if end_block_config == 'latest':
            end_block = latest_block_number
        else:
            end_block = int(end_block_config)
            
        logger.info(f"Sync target: blocks {start_block:,} to {end_block:,} ({end_block - start_block + 1:,} blocks)")
        logger.info(f"Current blockchain height: {latest_block_number:,}")
        
        # Confirmation
        print(f"\nSync Configuration:")
        print(f"  - Start block: {start_block:,}")
        print(f"  - End block: {end_block:,}")
        print(f"  - Total blocks to sync: {end_block - start_block + 1:,}")
        print(f"  - Analytics enabled: ✅")
        print(f"    • Token transfers: ✅")
        print(f"    • DEX swaps: ✅") 
        print(f"    • DeFi protocols: ✅")
        
        if start_block <= end_block:
            print(f"\n⚠️  This will process {end_block - start_block + 1:,} blocks with full analytics.")
            print("   This may take a significant amount of time and storage space.")
            
            # Start sync
            await processor.sync_range_with_analytics(start_block, end_block)
        else:
            logger.info("No blocks to sync - already up to date!")
            
    except KeyboardInterrupt:
        logger.info("Sync interrupted by user")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise
        
    finally:
        print("\n" + "=" * 70)
        print("🏁 SYNC PROCESS COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())