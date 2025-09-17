"""
Advanced Analytics Coordinator
Integrates token analytics, DEX analytics, and DeFi analytics modules.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from influxdb_client import Point
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.token_analytics import TokenAnalytics, TokenTransfer
from analytics.dex_analytics import DEXAnalytics, SwapEvent, LiquidityEvent
from analytics.defi_analytics import DeFiAnalytics, LendingEvent, StakingEvent, YieldEvent

logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """Coordinates all advanced analytics modules."""
    
    def __init__(self, blockchain_client, db_client, config):
        self.blockchain_client = blockchain_client
        self.db_client = db_client
        self.config = config
        
        # Initialize analytics modules
        self.token_analytics = TokenAnalytics(blockchain_client, db_client, config)
        self.dex_analytics = DEXAnalytics(blockchain_client, db_client, config)
        self.defi_analytics = DeFiAnalytics(blockchain_client, db_client, config)
        
        # Analytics configuration
        self.analytics_config = config.get('analytics', {})
        self.enabled_modules = {
            'token_transfers': self.analytics_config.get('track_erc20_transfers', True),
            'dex_swaps': self.analytics_config.get('track_dex_swaps', True),
            'liquidity_changes': self.analytics_config.get('track_liquidity_changes', True),
            'lending_protocols': self.analytics_config.get('track_lending_protocols', True),
            'yield_farming': self.analytics_config.get('track_yield_farming', True),
            'staking': self.analytics_config.get('track_staking', True),
        }
        
        # Statistics
        self.stats = {
            'token_transfers_found': 0,
            'dex_swaps_found': 0,
            'liquidity_events_found': 0,
            'lending_events_found': 0,
            'staking_events_found': 0,
            'yield_events_found': 0,
            'blocks_processed': 0,
            'transactions_analyzed': 0,
            'total_events_found': 0,
        }
        
    async def analyze_transaction(self, tx_data: Dict[str, Any], receipt: Dict[str, Any], 
                                block_timestamp: datetime) -> Dict[str, Any]:
        """Analyze a transaction for all enabled analytics."""
        analysis_results = {
            'token_transfers': [],
            'dex_swaps': [],
            'liquidity_events': [],
            'lending_events': [],
            'staking_events': [],
            'yield_events': [],
            'total_events': 0
        }
        
        if not receipt or 'logs' not in receipt:
            return analysis_results
            
        try:
            # Token Analytics
            if self.enabled_modules['token_transfers']:
                token_transfers = await self.token_analytics.analyze_transaction_logs(
                    tx_data, receipt, block_timestamp
                )
                analysis_results['token_transfers'] = token_transfers
                self.stats['token_transfers_found'] += len(token_transfers)
                
                if token_transfers:
                    logger.debug(f"Found {len(token_transfers)} token transfers in tx {tx_data.get('hash', 'unknown')}")
                    self.token_analytics.store_token_transfers(token_transfers)
                    
            # DEX Analytics
            if self.enabled_modules['dex_swaps'] or self.enabled_modules['liquidity_changes']:
                dex_swaps, liquidity_events = await self.dex_analytics.analyze_dex_logs(
                    tx_data, receipt, block_timestamp
                )
                
                if self.enabled_modules['dex_swaps']:
                    analysis_results['dex_swaps'] = dex_swaps
                    self.stats['dex_swaps_found'] += len(dex_swaps)
                    
                    if dex_swaps:
                        logger.debug(f"Found {len(dex_swaps)} DEX swaps in tx {tx_data.get('hash', 'unknown')}")
                        self.dex_analytics.store_swaps(dex_swaps)
                        
                if self.enabled_modules['liquidity_changes']:
                    analysis_results['liquidity_events'] = liquidity_events
                    self.stats['liquidity_events_found'] += len(liquidity_events)
                    
                    if liquidity_events:
                        logger.debug(f"Found {len(liquidity_events)} liquidity events in tx {tx_data.get('hash', 'unknown')}")
                        self.dex_analytics.store_liquidity_events(liquidity_events)
                        
            # DeFi Analytics
            if any(self.enabled_modules[key] for key in ['lending_protocols', 'staking', 'yield_farming']):
                lending_events, staking_events, yield_events = await self.defi_analytics.analyze_defi_logs(
                    tx_data, receipt, block_timestamp
                )
                
                if self.enabled_modules['lending_protocols']:
                    analysis_results['lending_events'] = lending_events
                    self.stats['lending_events_found'] += len(lending_events)
                    
                    if lending_events:
                        logger.debug(f"Found {len(lending_events)} lending events in tx {tx_data.get('hash', 'unknown')}")
                        self.defi_analytics.store_lending_events(lending_events)
                        
                if self.enabled_modules['staking']:
                    analysis_results['staking_events'] = staking_events
                    self.stats['staking_events_found'] += len(staking_events)
                    
                    if staking_events:
                        logger.debug(f"Found {len(staking_events)} staking events in tx {tx_data.get('hash', 'unknown')}")
                        self.defi_analytics.store_staking_events(staking_events)
                        
                if self.enabled_modules['yield_farming']:
                    analysis_results['yield_events'] = yield_events
                    self.stats['yield_events_found'] += len(yield_events)
                    
                    if yield_events:
                        logger.debug(f"Found {len(yield_events)} yield farming events in tx {tx_data.get('hash', 'unknown')}")
                        self.defi_analytics.store_yield_events(yield_events)
                        
            # Calculate totals
            analysis_results['total_events'] = sum([
                len(analysis_results['token_transfers']),
                len(analysis_results['dex_swaps']),
                len(analysis_results['liquidity_events']),
                len(analysis_results['lending_events']),
                len(analysis_results['staking_events']),
                len(analysis_results['yield_events'])
            ])
            
            self.stats['total_events_found'] += analysis_results['total_events']
            
        except Exception as e:
            logger.error(f"Error in advanced analytics for tx {tx_data.get('hash', 'unknown')}: {e}")
            
        self.stats['transactions_analyzed'] += 1
        return analysis_results
        
    async def analyze_block(self, block_data: Dict[str, Any], block_timestamp: datetime) -> Dict[str, Any]:
        """Analyze all transactions in a block."""
        block_results = {
            'block_number': int(block_data.get('number', '0x0'), 16),
            'transactions_processed': 0,
            'total_events_found': 0,
            'token_transfers': 0,
            'dex_swaps': 0,
            'liquidity_events': 0,
            'lending_events': 0,
            'staking_events': 0,
            'yield_events': 0,
        }
        
        if 'transactions' not in block_data:
            return block_results
            
        for tx in block_data['transactions']:
            if isinstance(tx, dict):
                try:
                    # Get transaction receipt for logs
                    receipt = await self.blockchain_client.get_transaction_receipt(tx['hash'])
                    if receipt:
                        tx_results = await self.analyze_transaction(tx, receipt, block_timestamp)
                        
                        # Aggregate results
                        block_results['token_transfers'] += len(tx_results['token_transfers'])
                        block_results['dex_swaps'] += len(tx_results['dex_swaps'])
                        block_results['liquidity_events'] += len(tx_results['liquidity_events'])
                        block_results['lending_events'] += len(tx_results['lending_events'])
                        block_results['staking_events'] += len(tx_results['staking_events'])
                        block_results['yield_events'] += len(tx_results['yield_events'])
                        block_results['total_events_found'] += tx_results['total_events']
                        
                    block_results['transactions_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error analyzing transaction {tx.get('hash', 'unknown')}: {e}")
                    
        self.stats['blocks_processed'] += 1
        
        if block_results['total_events_found'] > 0:
            logger.info(
                f"Block {block_results['block_number']}: "
                f"Found {block_results['total_events_found']} total events "
                f"(Tokens: {block_results['token_transfers']}, "
                f"DEX: {block_results['dex_swaps']}, "
                f"Liquidity: {block_results['liquidity_events']}, "
                f"Lending: {block_results['lending_events']}, "
                f"Staking: {block_results['staking_events']}, "
                f"Yield: {block_results['yield_events']})"
            )
        
        return block_results
        
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get summary of analytics processing."""
        return {
            'enabled_modules': self.enabled_modules,
            'statistics': self.stats.copy(),
            'processing_rates': {
                'events_per_block': round(self.stats['total_events_found'] / max(self.stats['blocks_processed'], 1), 2),
                'events_per_transaction': round(self.stats['total_events_found'] / max(self.stats['transactions_analyzed'], 1), 4),
            }
        }
        
    async def calculate_comprehensive_metrics(self, time_period: str = "24h") -> Dict[str, Any]:
        """Calculate comprehensive analytics metrics."""
        metrics = {
            'time_period': time_period,
            'token_metrics': {},
            'dex_metrics': {},
            'defi_metrics': {},
            'summary': {}
        }
        
        try:
            # This would query InfluxDB for comprehensive metrics
            if self.db_client:
                # Token metrics - most active tokens by transfer volume
                # DEX metrics - trading volumes, liquidity changes
                # DeFi metrics - TVL changes, protocol activity
                pass
                
            metrics['summary'] = {
                'total_unique_tokens': 0,
                'total_trading_volume': 0,
                'total_liquidity_provided': 0,
                'total_value_locked': 0,
                'active_protocols': 0,
                'unique_users': 0,
            }
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive metrics: {e}")
            
        return metrics
        
    def store_analytics_summary(self, summary: Dict[str, Any]):
        """Store analytics processing summary to database."""
        if not self.db_client:
            return
            
        try:
            point = Point("analytics_summary") \
                .tag("analytics_version", "1.0") \
                .field("blocks_processed", summary['statistics']['blocks_processed']) \
                .field("transactions_analyzed", summary['statistics']['transactions_analyzed']) \
                .field("total_events_found", summary['statistics']['total_events_found']) \
                .field("token_transfers_found", summary['statistics']['token_transfers_found']) \
                .field("dex_swaps_found", summary['statistics']['dex_swaps_found']) \
                .field("liquidity_events_found", summary['statistics']['liquidity_events_found']) \
                .field("lending_events_found", summary['statistics']['lending_events_found']) \
                .field("staking_events_found", summary['statistics']['staking_events_found']) \
                .field("yield_events_found", summary['statistics']['yield_events_found']) \
                .field("events_per_block", summary['processing_rates']['events_per_block']) \
                .field("events_per_transaction", summary['processing_rates']['events_per_transaction']) \
                .time(datetime.now(timezone.utc))
            
            self.db_client.write_batch([point])
            logger.debug("Stored analytics summary to database")
            
        except Exception as e:
            logger.error(f"Error storing analytics summary: {e}")


# Integration with existing processors
def add_analytics_to_processor(processor_class):
    """Decorator to add advanced analytics to existing processors."""
    
    original_process_single_block = processor_class.process_single_block
    original_init = processor_class.__init__
    
    def new_init(self, config):
        original_init(self, config)
        self.advanced_analytics = AdvancedAnalytics(
            self.blockchain_client, 
            self.db_client, 
            config
        )
        
    async def new_process_single_block(self, block_data, block_number):
        # Call original processing
        result = await original_process_single_block(self, block_data, block_number)
        
        # Add advanced analytics
        if hasattr(self, 'advanced_analytics'):
            try:
                block_timestamp = datetime.fromtimestamp(int(block_data.get('timestamp', '0x0'), 16))
                analytics_result = await self.advanced_analytics.analyze_block(block_data, block_timestamp)
                
                # Add analytics results to the original result
                if isinstance(result, dict):
                    result['analytics'] = analytics_result
                    
            except Exception as e:
                logger.error(f"Error in analytics enhancement for block {block_number}: {e}")
                
        return result
        
    processor_class.__init__ = new_init
    processor_class.process_single_block = new_process_single_block
    
    return processor_class


async def test_advanced_analytics():
    """Test the advanced analytics coordinator."""
    from core.config import Config
    from core.blockchain_client import BlockchainClient
    from core.influxdb_client import BlockchainInfluxDB
    
    config = Config()
    blockchain_client = BlockchainClient(config.blockchain_rpc_url)
    
    db_client = None
    if config.influxdb_token:
        db_client = BlockchainInfluxDB(
            url=config.influxdb_url,
            token=config.influxdb_token,
            org=config.influxdb_org,
            bucket=config.influxdb_bucket
        )
        await db_client.connect()
    
    advanced_analytics = AdvancedAnalytics(blockchain_client, db_client, config)
    
    try:
        await blockchain_client.connect()
        latest_block = await blockchain_client.get_latest_block_number()
        
        if latest_block:
            test_block = latest_block - 2
            block_data = await blockchain_client.get_block(test_block, include_transactions=True)
            
            if block_data:
                print(f"Testing advanced analytics with block {test_block}")
                
                block_timestamp = datetime.fromtimestamp(int(block_data.get('timestamp', '0x0'), 16))
                results = await advanced_analytics.analyze_block(block_data, block_timestamp)
                
                print(f"Analysis Results:")
                print(f"  Transactions processed: {results['transactions_processed']}")
                print(f"  Total events found: {results['total_events_found']}")
                print(f"  Token transfers: {results['token_transfers']}")
                print(f"  DEX swaps: {results['dex_swaps']}")
                print(f"  Liquidity events: {results['liquidity_events']}")
                print(f"  Lending events: {results['lending_events']}")
                print(f"  Staking events: {results['staking_events']}")
                print(f"  Yield events: {results['yield_events']}")
                
                summary = advanced_analytics.get_analytics_summary()
                print(f"\\nOverall Statistics:")
                print(f"  Blocks processed: {summary['statistics']['blocks_processed']}")
                print(f"  Transactions analyzed: {summary['statistics']['transactions_analyzed']}")
                print(f"  Total events found: {summary['statistics']['total_events_found']}")
                print(f"  Events per block: {summary['processing_rates']['events_per_block']}")
                
                if db_client:
                    advanced_analytics.store_analytics_summary(summary)
                    
    except Exception as e:
        print(f"Test error: {e}")
    
    finally:
        if db_client:
            db_client.close()


if __name__ == "__main__":
    asyncio.run(test_advanced_analytics())