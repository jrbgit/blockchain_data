"""
Historical Data Processor - Clean Version
Processes historical blockchain data in parallel batches.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.blockchain_client import BlockchainClient
from core.influxdb_client import BlockchainInfluxDB
from core.config import Config
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


class HistoricalProcessor:
    """Processes historical blockchain data with parallel batching."""
    
    def __init__(self, config: Config):
        self.config = config
        self.blockchain_client = BlockchainClient(
            rpc_url=config.blockchain_rpc_url,
            max_connections=config.max_connections,
            timeout=config.connection_timeout
        )
        
        # InfluxDB client (will be initialized when token is available)
        self.db_client = None
        if config.influxdb_token:
            self.db_client = BlockchainInfluxDB(
                url=config.influxdb_url,
                token=config.influxdb_token,
                org=config.influxdb_org,
                bucket=config.influxdb_bucket
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
            'blocks_per_second': 0.0
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
            f"Initialization complete - Blockchain: {blockchain_connected}, "
            f"Database: {db_connected}, Chain ID: {self.blockchain_client.chain_id}"
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
            'batch_end': end_block
        }
        
        try:
            # Get blocks in batch
            blocks = await self.blockchain_client.get_blocks_batch(start_block, end_block)
            
            for i, block in enumerate(blocks):
                block_number = start_block + i
                
                if isinstance(block, Exception):
                    logger.error(f"Error getting block {block_number}: {block}")
                    batch_stats['errors'] += 1
                    continue
                    
                if block is None:
                    logger.warning(f"Block {block_number} returned None")
                    batch_stats['errors'] += 1
                    continue
                    
                # Process the block
                block_stats = await self.process_single_block(block, block_number)
                batch_stats['blocks_processed'] += 1
                batch_stats['transactions_processed'] += block_stats.get('transactions', 0)
                batch_stats['events_processed'] += block_stats.get('events', 0)
                
        except Exception as e:
            logger.error(f"Error processing batch {start_block}-{end_block}: {e}")
            batch_stats['errors'] += 1
            
        return batch_stats
        
    async def process_single_block(self, block_data: Dict[str, Any], block_number: int) -> Dict[str, Any]:
        """Process a single block and its transactions."""
        block_stats = {'transactions': 0, 'events': 0}
        
        try:
            # Store block data
            if self.db_client:
                self.db_client.write_block(block_data)
                
            # Process transactions
            transactions = block_data.get('transactions', [])
            for tx in transactions:
                if isinstance(tx, dict):  # Full transaction object
                    await self.process_transaction(tx, block_number)
                    block_stats['transactions'] += 1
                    
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
            
    async def run_historical_processing(self, max_blocks: int = 100) -> bool:
        """Run the historical processing."""
        logger.info("Starting historical blockchain data processing...")
        
        try:
            # Initialize connections
            if not await self.initialize():
                return False
                
            # Determine processing range
            start_block, end_block = await self.get_processing_range()
            
            # Limit blocks for testing
            if max_blocks > 0:
                end_block = min(end_block, start_block + max_blocks - 1)
            
            total_blocks = end_block - start_block + 1
            
            if total_blocks <= 0:
                logger.info("No blocks to process")
                return True
                
            logger.info(f"Processing blocks {start_block} to {end_block} ({total_blocks} blocks)")
            
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
                    f"Processing {total_blocks} blocks...", 
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
                    
                    # Update progress
                    blocks_in_batch = batch_end - current_block + 1
                    progress.update(task, advance=blocks_in_batch)
                    
                    # Update rate calculation
                    elapsed = time.time() - self.stats['start_time']
                    if elapsed > 0:
                        self.stats['blocks_per_second'] = self.stats['blocks_processed'] / elapsed
                        
                    current_block = batch_end + 1
                    
            # Final statistics
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
        table.add_row("Errors", str(self.stats['errors']))
        table.add_row("Total Time", f"{total_time:.2f} seconds")
        table.add_row("Average Rate", f"{self.stats['blocks_per_second']:.2f} blocks/sec")
        
        console.print(table)


async def main():
    """Main function to run historical processing."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/historical_processing.log')
        ]
    )
    
    # Load configuration
    config = Config()
    
    # Create and run processor
    processor = HistoricalProcessor(config)
    success = await processor.run_historical_processing(max_blocks=0)  # Process all blocks (0 = no limit)
    
    if success:
        console.print("\n[bold green]✅ Historical processing completed successfully![/bold green]")
    else:
        console.print("\n[bold red]❌ Historical processing failed![/bold red]")
        
    return success


if __name__ == "__main__":
    asyncio.run(main())