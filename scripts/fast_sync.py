#!/usr/bin/env python3
"""
High-Performance Blockchain Sync Script
Optimized for maximum sync throughput with minimal overhead.

Key optimizations:
- Parallel block fetching (10-50 concurrent requests)
- Large batch sizes (1000+ blocks)
- Batch database writes
- Skip expensive operations during initial sync
- Smart resume capability
- Connection pooling
"""

import asyncio
import logging
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / \"src\"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB
from core.blockchain_client import BlockchainClient
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich.table import Table
from rich.live import Live
import aiohttp
import asyncio
import structlog

console = Console()
logger = structlog.get_logger(__name__)

class HighPerformanceSync:
    """High-performance blockchain sync with maximum throughput optimizations."""
    
    def __init__(self):
        self.config = Config()
        self.db_client = None
        self.blockchain_client = None
        
        # Performance settings - optimized for speed
        self.batch_size = 2000  # Much larger batches
        self.concurrent_requests = 20  # Parallel block fetching
        self.max_workers = mp.cpu_count() * 2  # Scale with CPU cores
        self.checkpoint_interval = 5000  # Save progress every 5000 blocks
        
        # Connection pool settings
        self.connection_pool_size = 50
        self.connection_timeout = 60
        
        # Database batch settings
        self.db_batch_size = 1000
        self.pending_writes = []
        
        # Performance tracking
        self.stats = {
            'blocks_processed': 0,
            'start_time': None,
            'last_checkpoint_time': None,
            'blocks_per_second': 0.0,
            'estimated_completion': None,
            'errors': 0,
            'retries': 0
        }
        
        # Resume state
        self.checkpoint_file = "sync_checkpoint.json"
        
    async def initialize(self) -> bool:
        """Initialize connections with optimized settings."""
        console.print(Panel(
            Text("🚀 High-Performance Sync - Initializing", style="bold cyan"),
            border_style="cyan"
        ))
        
        try:
            # Initialize blockchain client with optimized settings
            self.blockchain_client = BlockchainClient(
                self.config,
                max_connections=self.connection_pool_size,
                timeout=self.connection_timeout
            )
            
            blockchain_connected = await self.blockchain_client.connect()
            if not blockchain_connected:
                console.print("❌ Failed to connect to blockchain")
                return False
            
            console.print("✅ Connected to GLQ Chain")
            console.print(f"   Chain ID: {self.blockchain_client.chain_id}")
            console.print(f"   Connection pool: {self.connection_pool_size} connections")
            
            # Initialize database client
            if self.config.influxdb_token:
                self.db_client = BlockchainInfluxDB(self.config)
                db_connected = await self.db_client.connect()
                
                if not db_connected:
                    console.print("❌ Failed to connect to InfluxDB")
                    return False
                    
                console.print("✅ Connected to InfluxDB")
                console.print(f"   Database batch size: {self.db_batch_size}")
            else:
                console.print("❌ No InfluxDB token configured")
                return False
            
            # Display optimization settings
            console.print(f"\n🔧 Performance Settings:")
            console.print(f"   Batch size: {self.batch_size:,} blocks")
            console.print(f"   Concurrent requests: {self.concurrent_requests}")
            console.print(f"   Max workers: {self.max_workers}")
            console.print(f"   Checkpoint interval: {self.checkpoint_interval:,} blocks")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Initialization failed: {e}")
            logger.error(f"Initialization error: {e}", exc_info=True)
            return False
    
    def load_checkpoint(self) -> Optional[int]:
        """Load sync progress from checkpoint file."""
        try:
            if Path(self.checkpoint_file).exists():
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_synced_block', None)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
        return None
    
    def save_checkpoint(self, block_number: int):
        """Save sync progress to checkpoint file."""
        try:
            checkpoint_data = {
                'last_synced_block': block_number,
                'timestamp': datetime.utcnow().isoformat(),
                'blocks_processed': self.stats['blocks_processed'],
                'avg_blocks_per_second': self.stats['blocks_per_second']
            }
            
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    async def get_sync_range(self) -> Tuple[int, int]:
        """Determine the range of blocks to sync."""
        # Get latest block from blockchain
        latest_blockchain_block = await self.blockchain_client.get_latest_block_number()
        if latest_blockchain_block is None:
            raise ValueError("Could not get latest block from blockchain")
        
        # Check for existing checkpoint
        checkpoint_block = self.load_checkpoint()
        
        # Check database for latest block
        db_latest_block = None
        if self.db_client:
            try:
                db_latest_block = self.db_client.query_latest_block()
            except Exception as e:
                logger.warning(f"Could not query latest block from database: {e}")
        
        # Determine start block
        start_block = 1
        if checkpoint_block is not None:
            start_block = checkpoint_block + 1
            console.print(f"📄 Resuming from checkpoint: block {checkpoint_block:,}")
        elif db_latest_block is not None:
            start_block = db_latest_block + 1
            console.print(f"💾 Resuming from database: block {db_latest_block:,}")
        
        # Use a buffer from the latest block to avoid reorg issues
        end_block = latest_blockchain_block - 5
        
        return start_block, end_block
    
    async def fetch_block_batch(self, block_numbers: List[int]) -> List[Optional[Dict[str, Any]]]:
        """Fetch multiple blocks concurrently."""
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        async def fetch_single_block(block_number: int) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    # Fetch block without transactions initially for speed
                    # We can add transaction details in a second pass if needed
                    block_data = await self.blockchain_client.get_block(block_number, include_transactions=False)
                    
                    if block_data is None:
                        logger.warning(f"Block {block_number} returned None")
                        self.stats['errors'] += 1
                        return None
                    
                    # If we need transaction hashes for basic counting
                    if 'transactions' in block_data and isinstance(block_data['transactions'][0] if block_data['transactions'] else None, str):
                        # Transactions are just hashes, that's perfect for fast sync
                        pass
                    
                    return {
                        'block_number': block_number,
                        'block_data': block_data
                    }
                    
                except Exception as e:
                    logger.error(f"Error fetching block {block_number}: {e}")
                    self.stats['errors'] += 1
                    return None
        
        # Execute all block fetches concurrently
        tasks = [fetch_single_block(block_num) for block_num in block_numbers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        successful_blocks = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Block fetch exception: {result}")
                self.stats['errors'] += 1
            elif result is not None:
                successful_blocks.append(result)
        
        return successful_blocks
    
    def process_blocks_for_database(self, block_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process blocks into database points for batch writing."""
        points = []
        
        for block_info in block_batch:
            try:
                block_number = block_info['block_number']
                block_data = block_info['block_data']
                
                # Convert timestamp
                timestamp = datetime.fromtimestamp(int(block_data['timestamp'], 16))
                
                # Calculate gas utilization
                gas_used = int(block_data['gasUsed'], 16)
                gas_limit = int(block_data['gasLimit'], 16)
                gas_utilization = gas_used / gas_limit if gas_limit > 0 else 0
                
                # Create block point for InfluxDB
                block_point = {
                    "measurement": "blocks",
                    "tags": {
                        "chain_id": "614",
                        "network": "mainnet",
                        "miner": block_data.get('miner', '0x0000000000000000000000000000000000000000')
                    },
                    "fields": {
                        "block_number": block_number,
                        "gas_limit": gas_limit,
                        "gas_used": gas_used,
                        "transaction_count": len(block_data.get('transactions', [])),
                        "size": int(block_data.get('size', '0x0'), 16),
                        "difficulty": block_data.get('difficulty', '0x0'),
                        "total_difficulty": block_data.get('totalDifficulty', '0x0'),
                        "gas_utilization": gas_utilization
                    },
                    "time": timestamp
                }
                
                # Add base fee if available (EIP-1559)
                if 'baseFeePerGas' in block_data:
                    block_point["fields"]["base_fee_per_gas"] = int(block_data['baseFeePerGas'], 16)
                
                points.append(block_point)
                
            except Exception as e:
                logger.error(f"Error processing block {block_info.get('block_number', 'unknown')}: {e}")
                self.stats['errors'] += 1
        
        return points
    
    async def write_batch_to_database(self, points: List[Dict[str, Any]]):
        """Write a batch of points to the database."""
        if not points or not self.db_client:
            return
        
        try:
            # Use the optimized batch write method
            self.db_client.write_points(points)
            
        except Exception as e:
            logger.error(f"Error writing batch to database: {e}")
            self.stats['errors'] += 1
    
    async def sync_blocks(self) -> bool:
        """Main sync loop with high-performance optimizations."""
        try:
            # Get sync range
            start_block, end_block = await self.get_sync_range()
            total_blocks = end_block - start_block + 1
            
            if total_blocks <= 0:
                console.print("✅ Database is up to date!")
                return True
            
            console.print(Panel(
                Text(f"🚀 Starting High-Speed Sync", style="bold green"),
                subtitle=f"Blocks {start_block:,} to {end_block:,} ({total_blocks:,} blocks)",
                border_style="green"
            ))
            
            # Calculate estimated time with optimized rate
            estimated_blocks_per_second = 50  # Conservative estimate with optimizations
            estimated_hours = total_blocks / estimated_blocks_per_second / 3600
            console.print(f"⚡ Estimated completion time: ~{estimated_hours:.1f} hours")
            
            # Initialize stats
            self.stats['start_time'] = time.time()
            self.stats['last_checkpoint_time'] = time.time()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                TimeRemainingColumn(),
                TextColumn("Rate: {task.fields[rate]}"),
                console=console,
                refresh_per_second=2
            ) as progress:
                
                task = progress.add_task(
                    f"Syncing {total_blocks:,} blocks...", 
                    total=total_blocks,
                    rate="0.00 blocks/sec"
                )
                
                current_block = start_block
                
                while current_block <= end_block:
                    batch_start_time = time.time()
                    
                    # Determine batch end
                    batch_end = min(current_block + self.batch_size - 1, end_block)
                    batch_blocks = list(range(current_block, batch_end + 1))
                    
                    # Fetch blocks concurrently
                    block_results = await self.fetch_block_batch(batch_blocks)
                    
                    if block_results:
                        # Process blocks for database
                        db_points = self.process_blocks_for_database(block_results)
                        
                        # Write to database in batch
                        if db_points:
                            await self.write_batch_to_database(db_points)
                        
                        # Update statistics
                        blocks_processed = len(block_results)
                        self.stats['blocks_processed'] += blocks_processed
                        
                        # Calculate rate
                        elapsed_total = time.time() - self.stats['start_time']
                        if elapsed_total > 0:
                            self.stats['blocks_per_second'] = self.stats['blocks_processed'] / elapsed_total
                        
                        # Update progress
                        progress.update(
                            task, 
                            advance=blocks_processed,
                            rate=f"{self.stats['blocks_per_second']:.2f} blocks/sec"
                        )
                        
                        # Checkpoint progress periodically
                        if self.stats['blocks_processed'] % self.checkpoint_interval == 0:
                            self.save_checkpoint(batch_end)
                            
                            # Log detailed progress
                            checkpoint_time = time.time()
                            time_since_last = checkpoint_time - self.stats['last_checkpoint_time']
                            console.print(f"📊 Checkpoint: Block {batch_end:,}, "
                                        f"Rate: {self.stats['blocks_per_second']:.2f} blocks/sec, "
                                        f"Errors: {self.stats['errors']}")
                            self.stats['last_checkpoint_time'] = checkpoint_time
                    
                    current_block = batch_end + 1
                    
                    # Brief pause to prevent overwhelming the RPC
                    await asyncio.sleep(0.001)
            
            # Final checkpoint
            self.save_checkpoint(end_block)
            
            # Final statistics
            total_time = time.time() - self.stats['start_time']
            
            console.print(Panel(
                Text("🎉 High-Performance Sync Completed!", style="bold green"),
                border_style="green"
            ))
            
            # Create summary table
            table = Table(title="📊 Sync Performance Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Blocks Processed", f"{self.stats['blocks_processed']:,}")
            table.add_row("Total Time", f"{total_time:.2f} seconds ({total_time/3600:.2f} hours)")
            table.add_row("Average Rate", f"{self.stats['blocks_per_second']:.2f} blocks/sec")
            table.add_row("Errors", str(self.stats['errors']))
            table.add_row("Success Rate", f"{((self.stats['blocks_processed'] - self.stats['errors']) / max(self.stats['blocks_processed'], 1) * 100):.2f}%")
            
            console.print(table)
            
            return True
            
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            console.print(f"❌ Sync failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up connections."""
        if self.blockchain_client:
            self.blockchain_client.close()
        if self.db_client:
            self.db_client.close()

async def main():
    """Main function."""
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
    
    console.print(Panel(
        Text("⚡ GLQ Chain High-Performance Sync", style="bold white"),
        subtitle="Optimized for maximum throughput",
        border_style="white"
    ))
    
    sync_engine = HighPerformanceSync()
    
    try:
        # Initialize
        if not await sync_engine.initialize():
            console.print("❌ Initialization failed")
            return False
        
        # Run sync
        success = await sync_engine.sync_blocks()
        
        return success
        
    except KeyboardInterrupt:
        console.print("\n⚠️ Sync interrupted by user")
        return False
    except Exception as e:
        console.print(f"❌ Sync failed: {e}")
        logger.error(f"Main sync error: {e}", exc_info=True)
        return False
    finally:
        await sync_engine.cleanup()

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        sys.exit(0)
