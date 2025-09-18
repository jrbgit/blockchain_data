"""
Multi-Chain Data Processor

This module coordinates data processing across multiple blockchain networks,
handling chain-specific logic while maintaining unified data storage.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
import time
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

from ..core.config import Config
from ..core.multichain_client import MultiChainClient
from ..core.multichain_influxdb_client import MultiChainInfluxDB

logger = logging.getLogger(__name__)

@dataclass
class ChainProcessingStats:
    """Statistics for a single chain's processing"""
    chain_id: str
    chain_name: str
    blocks_processed: int = 0
    transactions_processed: int = 0
    events_processed: int = 0
    latest_block: Optional[int] = None
    target_block: Optional[int] = None
    processing_rate: float = 0.0  # blocks per second
    errors: int = 0
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, error, paused

@dataclass
class MultiChainProcessingSession:
    """Session tracking for multi-chain processing"""
    session_id: str
    enabled_chains: List[str]
    processing_type: str  # "historical", "realtime", "range"
    start_time: datetime
    stats_per_chain: Dict[str, ChainProcessingStats]
    total_blocks_processed: int = 0
    total_transactions_processed: int = 0


class MultiChainProcessor:
    """
    Coordinates data processing across multiple blockchain networks.
    Handles both historical sync and real-time processing.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        
        # Clients
        self.multichain_client: Optional[MultiChainClient] = None
        self.db_client: Optional[MultiChainInfluxDB] = None
        
        # Processing state
        self.active_chains: Set[str] = set()
        self.processing_sessions: Dict[str, MultiChainProcessingSession] = {}
        self.shutdown_requested = False
        
        # Performance settings
        self.batch_size = config.get('processing.batch_size', 100)
        self.max_concurrent_chains = config.get('processing.max_workers', 4)
        self.processing_delay = 0.1  # Small delay between batches
        
        logger.info("Initialized multi-chain processor")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
    
    async def connect(self):
        """Initialize connections to blockchain networks and database"""
        try:
            # Connect to multi-chain client
            self.multichain_client = MultiChainClient(self.config)
            await self.multichain_client.connect()
            
            # Connect to database
            self.db_client = MultiChainInfluxDB(self.config)
            await self.db_client.connect()
            
            # Get connected chains
            self.active_chains = set(self.multichain_client.get_connected_chains())
            
            logger.info(f"Multi-chain processor connected to {len(self.active_chains)} chains")
            
        except Exception as e:
            logger.error(f"Failed to connect multi-chain processor: {e}")
            raise
    
    async def process_historical_data(self, 
                                    chains: Optional[List[str]] = None,
                                    start_block: Optional[int] = None,
                                    max_blocks: Optional[int] = None) -> bool:
        """
        Process historical data for specified chains
        
        Args:
            chains: List of chain IDs to process, None for all connected chains
            start_block: Starting block number, None to resume from last processed
            max_blocks: Maximum number of blocks to process per chain
            
        Returns:
            True if processing completed successfully
        """
        if not chains:
            chains = list(self.active_chains)
        else:
            # Validate requested chains are connected
            chains = [c for c in chains if c in self.active_chains]
        
        if not chains:
            logger.error("No valid chains specified for historical processing")
            return False
        
        session_id = f"historical_{int(time.time())}"
        session = MultiChainProcessingSession(
            session_id=session_id,
            enabled_chains=chains,
            processing_type="historical",
            start_time=datetime.now(),
            stats_per_chain={}
        )
        
        # Initialize stats for each chain
        for chain_id in chains:
            chain_config = self.multichain_client.get_chain_config(chain_id)
            session.stats_per_chain[chain_id] = ChainProcessingStats(
                chain_id=chain_id,
                chain_name=chain_config['name'],
                start_time=datetime.now(),
                status="pending"
            )
        
        self.processing_sessions[session_id] = session
        
        try:
            # Determine starting points for each chain
            await self._determine_processing_ranges(session, start_block, max_blocks)
            
            # Process chains concurrently
            success = await self._process_chains_concurrent(session)
            
            # Final statistics
            self._log_session_summary(session)
            
            return success
            
        except Exception as e:
            logger.error(f"Historical processing failed: {e}")
            return False
        finally:
            # Cleanup
            if session_id in self.processing_sessions:
                del self.processing_sessions[session_id]
    
    async def process_realtime(self, 
                              chains: Optional[List[str]] = None,
                              polling_interval: int = 2) -> None:
        """
        Process real-time data for specified chains
        
        Args:
            chains: List of chain IDs to monitor, None for all connected chains
            polling_interval: Seconds between polling for new blocks
        """
        if not chains:
            chains = list(self.active_chains)
        else:
            chains = [c for c in chains if c in self.active_chains]
        
        if not chains:
            logger.error("No valid chains specified for real-time processing")
            return
        
        session_id = f"realtime_{int(time.time())}"
        session = MultiChainProcessingSession(
            session_id=session_id,
            enabled_chains=chains,
            processing_type="realtime",
            start_time=datetime.now(),
            stats_per_chain={}
        )
        
        # Initialize stats for each chain
        for chain_id in chains:
            chain_config = self.multichain_client.get_chain_config(chain_id)
            session.stats_per_chain[chain_id] = ChainProcessingStats(
                chain_id=chain_id,
                chain_name=chain_config['name'],
                start_time=datetime.now(),
                status="running"
            )
        
        self.processing_sessions[session_id] = session
        
        logger.info(f"Starting real-time processing for {len(chains)} chains")
        
        try:
            await self._realtime_processing_loop(session, polling_interval)
        except KeyboardInterrupt:
            logger.info("Real-time processing interrupted by user")
        except Exception as e:
            logger.error(f"Real-time processing failed: {e}")
        finally:
            # Cleanup
            if session_id in self.processing_sessions:
                del self.processing_sessions[session_id]
    
    async def _determine_processing_ranges(self, session: MultiChainProcessingSession,
                                         start_block: Optional[int], max_blocks: Optional[int]):
        """Determine processing ranges for each chain in the session"""
        
        for chain_id, stats in session.stats_per_chain.items():
            try:
                # Get current blockchain height
                latest_block = await self.multichain_client.get_latest_block_number(chain_id)
                stats.target_block = latest_block
                
                # Determine starting block
                if start_block is not None:
                    stats.latest_block = start_block
                else:
                    # Try to resume from last processed block in database
                    db_latest = self.db_client.query_latest_block(chain_id)
                    stats.latest_block = (db_latest + 1) if db_latest else 1
                
                # Apply max_blocks limit if specified
                if max_blocks and stats.latest_block:
                    stats.target_block = min(stats.target_block or 0, stats.latest_block + max_blocks - 1)
                
                logger.info(f"{stats.chain_name}: Will process blocks {stats.latest_block} to {stats.target_block}")
                
            except Exception as e:
                logger.error(f"Failed to determine range for {chain_id}: {e}")
                stats.status = "error"
                stats.errors += 1
    
    async def _process_chains_concurrent(self, session: MultiChainProcessingSession) -> bool:
        """Process multiple chains concurrently with progress tracking"""
        
        # Create processing tasks for each chain
        tasks = []
        valid_chains = [
            chain_id for chain_id, stats in session.stats_per_chain.items()
            if stats.status != "error" and stats.latest_block is not None
        ]
        
        if not valid_chains:
            logger.error("No valid chains to process")
            return False
        
        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            # Add progress task for each chain
            progress_tasks = {}
            for chain_id in valid_chains:
                stats = session.stats_per_chain[chain_id]
                total_blocks = (stats.target_block or 0) - (stats.latest_block or 0) + 1
                
                progress_tasks[chain_id] = progress.add_task(
                    f"Processing {stats.chain_name}",
                    total=total_blocks
                )
            
            # Create async tasks for processing
            for chain_id in valid_chains:
                task = asyncio.create_task(
                    self._process_single_chain(session, chain_id, progress, progress_tasks[chain_id])
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            success_count = 0
            for i, result in enumerate(results):
                chain_id = valid_chains[i]
                if isinstance(result, Exception):
                    logger.error(f"Chain {chain_id} processing failed: {result}")
                    session.stats_per_chain[chain_id].status = "error"
                elif result:
                    success_count += 1
                    session.stats_per_chain[chain_id].status = "completed"
                else:
                    session.stats_per_chain[chain_id].status = "error"
        
        return success_count > 0
    
    async def _process_single_chain(self, session: MultiChainProcessingSession,
                                   chain_id: str, progress: Progress, task_id: TaskID) -> bool:
        """Process a single chain's blocks"""
        
        stats = session.stats_per_chain[chain_id]
        stats.status = "running"
        
        try:
            current_block = stats.latest_block
            target_block = stats.target_block
            
            if not current_block or not target_block:
                logger.error(f"Invalid block range for {chain_id}")
                return False
            
            batch_start_time = time.time()
            
            while current_block <= target_block and not self.shutdown_requested:
                # Process batch of blocks
                batch_end = min(current_block + self.batch_size - 1, target_block)
                
                batch_success = await self._process_block_batch(
                    chain_id, current_block, batch_end, stats
                )
                
                if not batch_success:
                    logger.warning(f"Batch processing failed for {chain_id} blocks {current_block}-{batch_end}")
                    stats.errors += 1
                
                # Update progress
                blocks_processed = batch_end - current_block + 1
                progress.update(task_id, advance=blocks_processed)
                
                # Update statistics
                stats.blocks_processed += blocks_processed
                stats.last_update = datetime.now()
                
                # Calculate processing rate
                if stats.start_time:
                    elapsed = (datetime.now() - stats.start_time).total_seconds()
                    stats.processing_rate = stats.blocks_processed / elapsed if elapsed > 0 else 0
                
                # Move to next batch
                current_block = batch_end + 1
                
                # Small delay to prevent overwhelming the network
                await asyncio.sleep(self.processing_delay)
                
                # Update session totals
                session.total_blocks_processed += blocks_processed
            
            stats.status = "completed"
            return True
            
        except Exception as e:
            logger.error(f"Error processing chain {chain_id}: {e}")
            stats.status = "error"
            stats.errors += 1
            return False
    
    async def _process_block_batch(self, chain_id: str, start_block: int, end_block: int,
                                 stats: ChainProcessingStats) -> bool:
        """Process a batch of blocks for a single chain"""
        
        try:
            # Get blocks in batch
            blocks = await self.multichain_client.batch_get_blocks(chain_id, start_block, end_block)
            
            if not blocks:
                logger.warning(f"No blocks retrieved for {chain_id} range {start_block}-{end_block}")
                return False
            
            # Process each block
            for i, block_data in enumerate(blocks):
                if block_data is None:
                    continue
                
                block_number = start_block + i
                
                try:
                    # Write block data to database
                    self.db_client.write_block(chain_id, block_data)
                    
                    # Process transactions
                    transactions = block_data.get('transactions', [])
                    for tx_data in transactions:
                        if isinstance(tx_data, dict):  # Full transaction data
                            self.db_client.write_transaction(
                                chain_id, tx_data, block_number, "success"
                            )
                            stats.transactions_processed += 1
                    
                    # TODO: Process events/logs
                    # TODO: Process token transfers
                    # TODO: Run chain-specific analytics
                    
                except Exception as e:
                    logger.error(f"Error processing block {block_number} on {chain_id}: {e}")
                    stats.errors += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error retrieving blocks for {chain_id}: {e}")
            return False
    
    async def _realtime_processing_loop(self, session: MultiChainProcessingSession,
                                      polling_interval: int):
        """Main loop for real-time processing"""
        
        logger.info("Starting real-time processing loop")
        
        while not self.shutdown_requested:
            try:
                # Get latest blocks for all chains
                latest_blocks = await self.multichain_client.get_latest_blocks_all_chains()
                
                # Check each chain for new blocks
                processing_tasks = []
                for chain_id, chain_latest in latest_blocks.items():
                    if chain_id not in session.stats_per_chain or chain_latest is None:
                        continue
                    
                    stats = session.stats_per_chain[chain_id]
                    
                    # Check if we have new blocks to process
                    if stats.latest_block is None:
                        stats.latest_block = chain_latest
                    elif chain_latest > stats.latest_block:
                        # Process new blocks
                        task = asyncio.create_task(
                            self._process_realtime_blocks(chain_id, stats.latest_block + 1, chain_latest, stats)
                        )
                        processing_tasks.append(task)
                        stats.latest_block = chain_latest
                
                # Wait for all processing tasks
                if processing_tasks:
                    await asyncio.gather(*processing_tasks, return_exceptions=True)
                
                # Log current status
                self._log_realtime_status(session)
                
                # Wait before next poll
                await asyncio.sleep(polling_interval)
                
            except Exception as e:
                logger.error(f"Error in real-time processing loop: {e}")
                await asyncio.sleep(polling_interval)
    
    async def _process_realtime_blocks(self, chain_id: str, start_block: int, end_block: int,
                                     stats: ChainProcessingStats):
        """Process new blocks detected in real-time"""
        
        try:
            for block_number in range(start_block, end_block + 1):
                # Get single block
                block_data = await self.multichain_client.get_block(chain_id, block_number, True)
                
                if block_data:
                    # Write to database
                    self.db_client.write_block(chain_id, block_data)
                    
                    # Process transactions
                    transactions = block_data.get('transactions', [])
                    for tx_data in transactions:
                        if isinstance(tx_data, dict):
                            self.db_client.write_transaction(
                                chain_id, tx_data, block_number, "success"
                            )
                            stats.transactions_processed += 1
                    
                    stats.blocks_processed += 1
                    stats.last_update = datetime.now()
                    
                    logger.debug(f"Processed real-time block {block_number} on {chain_id}")
                
        except Exception as e:
            logger.error(f"Error processing real-time blocks for {chain_id}: {e}")
            stats.errors += 1
    
    def _log_session_summary(self, session: MultiChainProcessingSession):
        """Log summary statistics for a processing session"""
        
        duration = datetime.now() - session.start_time
        
        # Create summary table
        table = Table(title=f"Processing Session Summary - {session.session_id}")
        table.add_column("Chain", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Blocks", justify="right")
        table.add_column("Transactions", justify="right")
        table.add_column("Rate (blocks/s)", justify="right")
        table.add_column("Errors", justify="right", style="red")
        
        total_blocks = 0
        total_transactions = 0
        total_errors = 0
        
        for stats in session.stats_per_chain.values():
            table.add_row(
                stats.chain_name,
                stats.status.upper(),
                f"{stats.blocks_processed:,}",
                f"{stats.transactions_processed:,}",
                f"{stats.processing_rate:.2f}",
                str(stats.errors)
            )
            
            total_blocks += stats.blocks_processed
            total_transactions += stats.transactions_processed
            total_errors += stats.errors
        
        # Add totals row
        table.add_row(
            "TOTAL",
            "",
            f"{total_blocks:,}",
            f"{total_transactions:,}",
            f"{total_blocks/duration.total_seconds():.2f}" if duration.total_seconds() > 0 else "0.00",
            str(total_errors),
            style="bold"
        )
        
        self.console.print(table)
        
        logger.info(f"Session completed: {total_blocks:,} blocks, {total_transactions:,} transactions in {duration}")
    
    def _log_realtime_status(self, session: MultiChainProcessingSession):
        """Log current real-time processing status"""
        
        status_info = []
        for stats in session.stats_per_chain.values():
            status_info.append(
                f"{stats.chain_name}: Block {stats.latest_block or 'N/A'} "
                f"({stats.blocks_processed} processed, {stats.errors} errors)"
            )
        
        if status_info:
            logger.info("Real-time status: " + " | ".join(status_info))
    
    async def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status across all active sessions"""
        
        status = {
            "active_chains": list(self.active_chains),
            "active_sessions": len(self.processing_sessions),
            "sessions": {}
        }
        
        for session_id, session in self.processing_sessions.items():
            session_status = {
                "type": session.processing_type,
                "start_time": session.start_time.isoformat(),
                "chains": {}
            }
            
            for chain_id, stats in session.stats_per_chain.items():
                session_status["chains"][chain_id] = {
                    "status": stats.status,
                    "blocks_processed": stats.blocks_processed,
                    "transactions_processed": stats.transactions_processed,
                    "processing_rate": stats.processing_rate,
                    "errors": stats.errors,
                    "latest_block": stats.latest_block,
                    "target_block": stats.target_block
                }
            
            status["sessions"][session_id] = session_status
        
        return status
    
    async def shutdown(self):
        """Gracefully shutdown the processor"""
        
        logger.info("Shutting down multi-chain processor...")
        self.shutdown_requested = True
        
        # Close connections
        if self.multichain_client:
            await self.multichain_client.close()
        
        if self.db_client:
            self.db_client.close()
        
        logger.info("Multi-chain processor shutdown complete")


# Convenience functions
async def run_historical_sync(config: Config, 
                            chains: Optional[List[str]] = None,
                            max_blocks: Optional[int] = None) -> bool:
    """Convenience function to run historical sync"""
    
    async with MultiChainProcessor(config) as processor:
        return await processor.process_historical_data(
            chains=chains,
            max_blocks=max_blocks
        )

async def run_realtime_monitor(config: Config, 
                             chains: Optional[List[str]] = None,
                             polling_interval: int = 2):
    """Convenience function to run real-time monitoring"""
    
    async with MultiChainProcessor(config) as processor:
        await processor.process_realtime(
            chains=chains,
            polling_interval=polling_interval
        )