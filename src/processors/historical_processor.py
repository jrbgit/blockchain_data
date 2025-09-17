"""
Historical Data Processor
Processes historical blockchain data in parallel batches with analytics support.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count
import time

from core.blockchain_client import BlockchainClient
from core.influxdb_client import BlockchainInfluxDB
from core.config import Config
from analytics.advanced_analytics import AdvancedAnalytics
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
import structlog

logger = structlog.get_logger(__name__)
console = Console()


class HistoricalProcessor:
    """Processes historical blockchain data with parallel batching and analytics."""
    
    def __init__(self, config: Config):
        self.config = config
        self.blockchain_client = BlockchainClient(config)
        
        # InfluxDB client (will be initialized when token is available)
        self.db_client = None
        if config.influxdb_token:
            self.db_client = BlockchainInfluxDB(config)
        
        # Analytics coordinator
        self.analytics = None
        if self.db_client and config.is_analytics_enabled():
            self.analytics = AdvancedAnalytics(
                blockchain_client=self.blockchain_client,
                db_client=self.db_client,
                config=config
            )
        
        # Processing state
        self.start_block = config.processing_start_block
        self.batch_size = config.processing_batch_size
        self.max_workers = config.processing_max_workers
        
        # Statistics
        self.stats = {
            'blocks_processed': 0,
            'transactions_processed': 0,
            'events_processed': 0,
            'errors': 0,
            'start_time': None,
            'blocks_per_second': 0.0,
            # Analytics statistics
            'token_transfers_found': 0,
            'dex_swaps_found': 0,
            'liquidity_events_found': 0,
            'defi_events_found': 0,
            'total_analytics_events': 0
        }
        
    async def initialize(self) -> bool:
        """Initialize connections to blockchain and database."""
        logger.info("Initializing historical processor...")
        
        # Connect to blockchain
        blockchain_connected = await self.blockchain_client.connect()
        if not blockchain_connected:
            logger.error("Failed to connect to blockchain")
            return False
            
        # Connect to database if available
        db_connected = True
        if self.db_client:
            db_connected = await self.db_client.connect()
            if not db_connected:
                logger.warning("Database connection failed, will continue without storing data")
                
        logger.info(
            "Initialization complete",
            blockchain_connected=blockchain_connected,
            database_connected=db_connected,
            analytics_enabled=self.analytics is not None,
            chain_id=self.blockchain_client.chain_id
        )
        
        return True
        
    async def get_processing_range(self) -> tuple[int, int]:
        """Determine the range of blocks to process."""
        # Get latest block from blockchain
        latest_blockchain_block = await self.blockchain_client.get_latest_block_number()
        if latest_blockchain_block is None:
            raise ValueError("Could not get latest block from blockchain")
            
        # Determine end block
        if self.config.processing_end_block == "latest":
            end_block = latest_blockchain_block - self.config.confirmation_blocks
        else:
            end_block = min(int(self.config.processing_end_block), latest_blockchain_block)
            
        # Check if we have any existing data in InfluxDB
        start_block = self.start_block
        if self.db_client:
            try:
                latest_db_block = self.db_client.query_latest_block()
                if latest_db_block is not None:
                    start_block = max(start_block, latest_db_block + 1)
                    logger.info(f"Resuming from block {start_block} (database has up to {latest_db_block})")
            except Exception as e:
                logger.warning(f"Could not query latest block from database: {e}")
                
        return start_block, end_block
        
    async def process_block_batch(self, start_block: int, end_block: int) -> Dict[str, Any]:
        """Process a batch of blocks."""
        batch_stats = {
            'blocks_processed': 0,
            'transactions_processed': 0,
            'events_processed': 0,
            'errors': 0,
            'batch_start': start_block,
            'batch_end': end_block,
            'token_transfers': 0,
            'dex_swaps': 0,
            'liquidity_events': 0,
            'defi_events': 0
        }
        
        try:
            # Process blocks individually to maintain analytics integration
            for block_number in range(start_block, end_block + 1):
                try:
                    # Get block with transactions
                    block_data = await self.blockchain_client.get_block(block_number, include_transactions=True)
                    
                    if block_data is None:
                        logger.warning(f"Block {block_number} returned None")
                        batch_stats['errors'] += 1
                        continue
                    
                    # Process the block
                    block_stats = await self.process_single_block(block_data, block_number)
                    batch_stats['blocks_processed'] += 1
                    batch_stats['transactions_processed'] += block_stats.get('transactions', 0)
                    batch_stats['events_processed'] += block_stats.get('events', 0)
                    
                    # Add analytics stats
                    batch_stats['token_transfers'] += block_stats.get('token_transfers', 0)
                    batch_stats['dex_swaps'] += block_stats.get('dex_swaps', 0)
                    batch_stats['liquidity_events'] += block_stats.get('liquidity_events', 0)
                    batch_stats['defi_events'] += block_stats.get('defi_events', 0)
                    
                except Exception as e:
                    logger.error(f"Error processing block {block_number}: {e}")
                    batch_stats['errors'] += 1
                    
        except Exception as e:
            logger.error(f"Error processing batch {start_block}-{end_block}: {e}")
            batch_stats['errors'] += 1
            
        return batch_stats
        
    async def process_single_block(self, block_data: Dict[str, Any], block_number: int) -> Dict[str, Any]:
        """Process a single block and its transactions with analytics."""
        block_stats = {'transactions': 0, 'events': 0, 'token_transfers': 0, 'dex_swaps': 0, 'liquidity_events': 0, 'defi_events': 0}
        
        try:
            # Calculate block time if we have previous block
            block_time_diff = None
            if block_number > 0:
                try:
                    prev_block = await self.blockchain_client.get_block(block_number - 1, False)
                    if prev_block:
                        curr_timestamp = int(block_data['timestamp'], 16)
                        prev_timestamp = int(prev_block['timestamp'], 16)
                        block_time_diff = curr_timestamp - prev_timestamp
                except Exception as e:
                    logger.debug(f"Could not calculate block time for {block_number}: {e}")
            
            # Store block data
            if self.db_client:
                self.db_client.write_block(block_data, block_time_diff)
            
            # Run analytics on the block if enabled
            if self.analytics:
                try:
                    # Compute block timestamp
                    ts = datetime.fromtimestamp(int(block_data.get('timestamp', '0x0'), 16), tz=timezone.utc)
                    
                    # Analyze the block
                    analytics_results = await self.analytics.analyze_block(block_data, ts)
                    
                    # Update analytics statistics
                    block_stats['token_transfers'] = analytics_results.get('token_transfers', 0)
                    block_stats['dex_swaps'] = analytics_results.get('dex_swaps', 0)
                    block_stats['liquidity_events'] = analytics_results.get('liquidity_events', 0)
                    defi_events = analytics_results.get('lending_events', 0) + analytics_results.get('staking_events', 0) + analytics_results.get('yield_events', 0)
                    block_stats['defi_events'] = defi_events
                    
                except Exception as e:
                    logger.debug(f"Analytics failed for block {block_number}: {e}")
            
            # Process transactions
            transactions = block_data.get('transactions', [])
            for tx in transactions:
                if isinstance(tx, dict):  # Full transaction object
                    await self.process_transaction(tx, block_number)
                    block_stats['transactions'] += 1
                    
            # Get and process events/logs for this block
            if self.config.get('processing.extract_logs', True):
                events = await self.get_block_events(block_number)
                if events:
                    for event in events:
                        await self.process_event(event, block_number)
                        block_stats['events'] += 1
                        
        except Exception as e:
            logger.error(f"Error processing block {block_number}: {e}")
            
        return block_stats
        
    async def process_transaction(self, tx_data: Dict[str, Any], block_number: int):
        """Process a single transaction."""
        try:
            # Get transaction receipt for gas usage and status
            receipt = await self.blockchain_client.get_transaction_receipt(tx_data['hash'])
            
            gas_used = None
            status = "pending"
            
            if receipt:
                gas_used = int(receipt.get('gasUsed', '0x0'), 16)
                status = "success" if receipt.get('status') == '0x1' else "failed"
                
            # Store transaction data
            if self.db_client:
                self.db_client.write_transaction(tx_data, block_number, status, gas_used)
                
        except Exception as e:
            logger.debug(f"Error processing transaction {tx_data.get('hash', 'unknown')}: {e}")
            
    async def get_block_events(self, block_number: int) -> Optional[List[Dict[str, Any]]]:
        """Get all events/logs for a block."""
        try:
            return await self.blockchain_client.get_logs(block_number, block_number)
        except Exception as e:
            logger.debug(f"Error getting events for block {block_number}: {e}")
            return None
            
    async def process_event(self, event_data: Dict[str, Any], block_number: int):
        """Process a single event/log."""
        try:
            if self.db_client:
                tx_hash = event_data.get('transactionHash', '')
                self.db_client.write_event(event_data, block_number, tx_hash)
        except Exception as e:
            logger.debug(f"Error processing event: {e}")
            
    async def process_blocks(self) -> bool:
        """Run the complete historical processing."""
        logger.info("Starting historical blockchain data processing with analytics...")
        
        try:
            # Initialize connections
            if not await self.initialize():
                return False
                
            # Determine processing range
            start_block, end_block = await self.get_processing_range()
            total_blocks = end_block - start_block + 1
            
            if total_blocks <= 0:
                logger.info("No blocks to process (database is up to date)")
                return True
                
            logger.info(
                f"Processing blocks {start_block} to {end_block} ({total_blocks:,} blocks)"
            )
            
            # Start processing with progress tracking
            self.stats['start_time'] = time.time()
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                TimeRemainingColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task(
                    f"Processing {total_blocks:,} blocks with analytics...", 
                    total=total_blocks
                )
                
                # Process in batches
                current_block = start_block
                
                while current_block <= end_block:
                    batch_end = min(current_block + self.batch_size - 1, end_block)
                    
                    # Process batch
                    batch_stats = await self.process_block_batch(current_block, batch_end)
                    
                    # Update statistics
                    self.stats['blocks_processed'] += batch_stats['blocks_processed']
                    self.stats['transactions_processed'] += batch_stats['transactions_processed']
                    self.stats['events_processed'] += batch_stats['events_processed']
                    self.stats['errors'] += batch_stats['errors']
                    
                    # Update analytics statistics
                    self.stats['token_transfers_found'] += batch_stats['token_transfers']
                    self.stats['dex_swaps_found'] += batch_stats['dex_swaps']
                    self.stats['liquidity_events_found'] += batch_stats['liquidity_events']
                    self.stats['defi_events_found'] += batch_stats['defi_events']
                    self.stats['total_analytics_events'] += (
                        batch_stats['token_transfers'] + batch_stats['dex_swaps'] + 
                        batch_stats['liquidity_events'] + batch_stats['defi_events']
                    )
                    
                    # Update progress
                    blocks_in_batch = batch_end - current_block + 1
                    progress.update(task, advance=blocks_in_batch)
                    
                    # Update rate calculation
                    elapsed = time.time() - self.stats['start_time']
                    if elapsed > 0:
                        self.stats['blocks_per_second'] = self.stats['blocks_processed'] / elapsed
                        
                    # Log progress
                    if self.stats['blocks_processed'] % (self.batch_size * 10) == 0:
                        logger.info(
                            "Processing progress",
                            blocks_processed=self.stats['blocks_processed'],
                            transactions=self.stats['transactions_processed'],
                            events=self.stats['events_processed'],
                            analytics_events=self.stats['total_analytics_events'],
                            rate_blocks_per_sec=f"{self.stats['blocks_per_second']:.2f}",
                            current_block=batch_end
                        )
                        
                    current_block = batch_end + 1
                    
            # Final statistics
            total_time = time.time() - self.stats['start_time']
            
            logger.info(
                "Historical processing completed",
                total_blocks=self.stats['blocks_processed'],
                total_transactions=self.stats['transactions_processed'],
                total_events=self.stats['events_processed'],
                total_analytics_events=self.stats['total_analytics_events'],
                total_errors=self.stats['errors'],
                total_time_seconds=f"{total_time:.2f}",
                avg_blocks_per_second=f"{self.stats['blocks_per_second']:.2f}"
            )
            
            self.print_final_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Historical processing failed: {e}")
            return False
        finally:
            # Clean up connections
            if self.blockchain_client:
                self.blockchain_client.close()
            if self.db_client:
                self.db_client.close()
                
    def print_final_summary(self):
        """Print a nice summary table."""
        table = Table(title="📊 Historical Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        total_time = time.time() - self.stats['start_time']
        
        table.add_row("Blocks Processed", f"{self.stats['blocks_processed']:,}")
        table.add_row("Transactions Processed", f"{self.stats['transactions_processed']:,}")
        table.add_row("Events Processed", f"{self.stats['events_processed']:,}")
        table.add_row("Token Transfers Found", f"{self.stats['token_transfers_found']:,}")
        table.add_row("DEX Swaps Found", f"{self.stats['dex_swaps_found']:,}")
        table.add_row("Liquidity Events Found", f"{self.stats['liquidity_events_found']:,}")
        table.add_row("DeFi Events Found", f"{self.stats['defi_events_found']:,}")
        table.add_row("Total Analytics Events", f"{self.stats['total_analytics_events']:,}")
        table.add_row("Errors", str(self.stats['errors']))
        table.add_row("Total Time", f"{total_time:.2f} seconds")
        table.add_row("Average Rate", f"{self.stats['blocks_per_second']:.2f} blocks/sec")
        
        console.print(table)


async def main():
    """Main function to run historical processing."""
    # Setup logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Load configuration
    config = Config()
    
    # Create and run processor
    processor = HistoricalProcessor(config)
    success = await processor.process_blocks()
    
    if success:
        console.print("\n[bold green]✅ Historical processing completed successfully![/bold green]")
    else:
        console.print("\n[bold red]❌ Historical processing failed![/bold red]")
        
    return success


if __name__ == "__main__":
    asyncio.run(main())