"""
DEX Analytics Module
Tracks decentralized exchange swaps, liquidity provision, and trading analytics.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class SwapEvent:
    """Represents a DEX swap event."""
    tx_hash: str
    block_number: int
    block_timestamp: datetime
    log_index: int
    dex_address: str
    dex_type: str  # 'UniswapV2', 'UniswapV3', 'SushiSwap', etc.
    sender: str
    recipient: str
    token_in: str
    token_out: str
    amount_in: int
    amount_out: int
    pair_address: Optional[str] = None
    pool_address: Optional[str] = None
    fee_tier: Optional[int] = None  # For V3 pools
    price_impact: Optional[float] = None


@dataclass
class LiquidityEvent:
    """Represents a liquidity provision/removal event."""
    tx_hash: str
    block_number: int
    block_timestamp: datetime
    log_index: int
    dex_address: str
    event_type: str  # 'mint', 'burn', 'add', 'remove'
    provider: str
    token0: str
    token1: str
    amount0: int
    amount1: int
    pair_address: str
    liquidity_delta: Optional[int] = None
    total_liquidity: Optional[int] = None


@dataclass
class TradingPair:
    """Trading pair information."""
    address: str
    token0: str
    token1: str
    dex_type: str
    fee_tier: Optional[int] = None
    total_supply: Optional[int] = None
    reserve0: Optional[int] = None
    reserve1: Optional[int] = None


class DEXAnalytics:
    """Handles DEX trading analysis and liquidity tracking."""
    
    # Uniswap V2 event signatures
    UNISWAP_V2_SWAP = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
    UNISWAP_V2_MINT = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"
    UNISWAP_V2_BURN = "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"
    UNISWAP_V2_SYNC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
    
    # Uniswap V3 event signatures
    UNISWAP_V3_SWAP = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    UNISWAP_V3_MINT = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
    UNISWAP_V3_BURN = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
    
    # Common DEX factory addresses (to be configured per chain)
    KNOWN_DEX_FACTORIES = {
        # These would be populated with actual GLQ chain DEX addresses
        "uniswap_v2_factory": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        "uniswap_v3_factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "sushiswap_factory": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
    }
    
    def __init__(self, blockchain_client, db_client, config):
        self.blockchain_client = blockchain_client
        self.db_client = db_client
        self.config = config
        self.pair_cache: Dict[str, TradingPair] = {}
        self.dex_factories = config.get('contracts', {}).get('dex_routers', [])
        
    async def analyze_dex_logs(self, tx_data: Dict[str, Any], receipt: Dict[str, Any],
                             block_timestamp: datetime) -> Tuple[List[SwapEvent], List[LiquidityEvent]]:
        """Analyze transaction logs for DEX activities."""
        swaps = []
        liquidity_events = []
        
        if not receipt or 'logs' not in receipt:
            return swaps, liquidity_events
            
        for log in receipt['logs']:
            try:
                if not log.get('topics'):
                    continue
                    
                topic0 = log['topics'][0] if isinstance(log['topics'][0], str) else log['topics'][0].hex()
                
                # Check for swap events
                if topic0 in [self.UNISWAP_V2_SWAP, self.UNISWAP_V3_SWAP]:
                    swap = await self._parse_swap_event(log, tx_data, block_timestamp, topic0)
                    if swap:
                        swaps.append(swap)
                        
                # Check for liquidity events
                elif topic0 in [self.UNISWAP_V2_MINT, self.UNISWAP_V2_BURN, 
                               self.UNISWAP_V3_MINT, self.UNISWAP_V3_BURN]:
                    liquidity_event = await self._parse_liquidity_event(log, tx_data, block_timestamp, topic0)
                    if liquidity_event:
                        liquidity_events.append(liquidity_event)
                        
            except Exception as e:
                logger.debug(f"Error parsing DEX log in tx {tx_data.get('hash', 'unknown')}: {e}")
                
        return swaps, liquidity_events
        
    async def _parse_swap_event(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                               block_timestamp: datetime, topic0: str) -> Optional[SwapEvent]:
        """Parse DEX swap event."""
        try:
            if topic0 == self.UNISWAP_V2_SWAP:
                return await self._parse_v2_swap(log, tx_data, block_timestamp)
            elif topic0 == self.UNISWAP_V3_SWAP:
                return await self._parse_v3_swap(log, tx_data, block_timestamp)
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing swap event: {e}")
            return None
            
    async def _parse_v2_swap(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                           block_timestamp: datetime) -> Optional[SwapEvent]:
        """Parse Uniswap V2 style swap event."""
        try:
            if len(log['topics']) < 3:
                return None
                
            pair_address = log['address']
            sender = self._address_from_topic(log['topics'][1])
            to_address = self._address_from_topic(log['topics'][2])
            
            # Parse swap data: amount0In, amount1In, amount0Out, amount1Out
            data = log.get('data', '0x')
            if len(data) < 258:  # 4 * 64 + 2 = 258 characters
                return None
                
            amount0_in = int(data[2:66], 16)
            amount1_in = int(data[66:130], 16) 
            amount0_out = int(data[130:194], 16)
            amount1_out = int(data[194:258], 16)
            
            # Determine swap direction and amounts
            if amount0_in > 0:
                amount_in = amount0_in
                amount_out = amount1_out
                # token_in is token0, token_out is token1
            else:
                amount_in = amount1_in
                amount_out = amount0_out
                # token_in is token1, token_out is token0
                
            # Get pair info (would need to fetch from contract)
            pair_info = await self.get_pair_info(pair_address)
            token_in = pair_info.token0 if amount0_in > 0 else pair_info.token1
            token_out = pair_info.token1 if amount0_in > 0 else pair_info.token0
            
            return SwapEvent(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                dex_address=pair_address,
                dex_type="UniswapV2",
                sender=sender,
                recipient=to_address,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=amount_out,
                pair_address=pair_address
            )
            
        except Exception as e:
            logger.debug(f"Error parsing V2 swap: {e}")
            return None
            
    async def _parse_v3_swap(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                           block_timestamp: datetime) -> Optional[SwapEvent]:
        """Parse Uniswap V3 style swap event."""
        try:
            if len(log['topics']) < 3:
                return None
                
            pool_address = log['address']
            sender = self._address_from_topic(log['topics'][1])
            recipient = self._address_from_topic(log['topics'][2])
            
            # V3 swaps have more complex data structure
            data = log.get('data', '0x')
            if len(data) < 194:  # Simplified parsing
                return None
                
            amount0 = int(data[2:66], 16)
            amount1 = int(data[66:130], 16)
            
            # Convert from two's complement if negative
            if amount0 > 2**255:
                amount0 -= 2**256
            if amount1 > 2**255:
                amount1 -= 2**256
                
            amount_in = abs(amount0) if amount0 < 0 else abs(amount1)
            amount_out = abs(amount0) if amount0 > 0 else abs(amount1)
            
            # Get pool info
            pool_info = await self.get_pair_info(pool_address)
            token_in = pool_info.token0 if amount0 < 0 else pool_info.token1
            token_out = pool_info.token1 if amount0 < 0 else pool_info.token0
            
            return SwapEvent(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                dex_address=pool_address,
                dex_type="UniswapV3",
                sender=sender,
                recipient=recipient,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=amount_out,
                pool_address=pool_address
            )
            
        except Exception as e:
            logger.debug(f"Error parsing V3 swap: {e}")
            return None
            
    async def _parse_liquidity_event(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                                   block_timestamp: datetime, topic0: str) -> Optional[LiquidityEvent]:
        """Parse liquidity provision/removal event."""
        try:
            if topic0 in [self.UNISWAP_V2_MINT, self.UNISWAP_V2_BURN]:
                return await self._parse_v2_liquidity(log, tx_data, block_timestamp, topic0)
            elif topic0 in [self.UNISWAP_V3_MINT, self.UNISWAP_V3_BURN]:
                return await self._parse_v3_liquidity(log, tx_data, block_timestamp, topic0)
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing liquidity event: {e}")
            return None
            
    async def _parse_v2_liquidity(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                                block_timestamp: datetime, topic0: str) -> Optional[LiquidityEvent]:
        """Parse Uniswap V2 liquidity event."""
        try:
            pair_address = log['address']
            sender = self._address_from_topic(log['topics'][1])
            
            data = log.get('data', '0x')
            if len(data) < 130:
                return None
                
            amount0 = int(data[2:66], 16)
            amount1 = int(data[66:130], 16)
            
            event_type = "mint" if topic0 == self.UNISWAP_V2_MINT else "burn"
            
            pair_info = await self.get_pair_info(pair_address)
            
            return LiquidityEvent(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                dex_address=pair_address,
                event_type=event_type,
                provider=sender,
                token0=pair_info.token0,
                token1=pair_info.token1,
                amount0=amount0,
                amount1=amount1,
                pair_address=pair_address
            )
            
        except Exception as e:
            logger.debug(f"Error parsing V2 liquidity event: {e}")
            return None
            
    async def _parse_v3_liquidity(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                                block_timestamp: datetime, topic0: str) -> Optional[LiquidityEvent]:
        """Parse Uniswap V3 liquidity event."""
        try:
            pool_address = log['address']
            
            # V3 liquidity events are more complex - simplified parsing
            data = log.get('data', '0x')
            if len(data) < 130:
                return None
                
            amount0 = int(data[2:66], 16)
            amount1 = int(data[66:130], 16)
            
            event_type = "mint" if topic0 == self.UNISWAP_V3_MINT else "burn"
            
            pool_info = await self.get_pair_info(pool_address)
            
            return LiquidityEvent(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                dex_address=pool_address,
                event_type=event_type,
                provider=tx_data['from'],  # Simplified - would get from topics
                token0=pool_info.token0,
                token1=pool_info.token1,
                amount0=amount0,
                amount1=amount1,
                pair_address=pool_address
            )
            
        except Exception as e:
            logger.debug(f"Error parsing V3 liquidity event: {e}")
            return None
            
    def _address_from_topic(self, topic: str) -> str:
        """Extract address from log topic."""
        if hasattr(topic, 'hex'):
            topic = topic.hex()
        addr = topic[-40:]
        return f"0x{addr}"
        
    async def get_pair_info(self, pair_address: str) -> TradingPair:
        """Get trading pair information."""
        if pair_address in self.pair_cache:
            return self.pair_cache[pair_address]
            
        try:
            # In a real implementation, this would fetch from the pair contract
            # For now, return a placeholder
            pair_info = TradingPair(
                address=pair_address,
                token0="0x0000000000000000000000000000000000000000",  # Would fetch from contract
                token1="0x0000000000000000000000000000000000000001",  # Would fetch from contract
                dex_type="Unknown"
            )
            
            self.pair_cache[pair_address] = pair_info
            return pair_info
            
        except Exception as e:
            logger.debug(f"Error getting pair info for {pair_address}: {e}")
            # Return default pair info
            return TradingPair(
                address=pair_address,
                token0="0x0000000000000000000000000000000000000000",
                token1="0x0000000000000000000000000000000000000001",
                dex_type="Unknown"
            )
            
    def store_swaps(self, swaps: List[SwapEvent]):
        """Store DEX swaps to database."""
        if not self.db_client or not swaps:
            return
            
        try:
            points = []
            for swap in swaps:
                point = {
                    "measurement": "dex_swaps",
                    "time": swap.block_timestamp,
                    "tags": {
                        "tx_hash": swap.tx_hash,
                        "dex_address": swap.dex_address,
                        "dex_type": swap.dex_type,
                        "sender": swap.sender,
                        "recipient": swap.recipient,
                        "token_in": swap.token_in,
                        "token_out": swap.token_out,
                        "pair_address": swap.pair_address or "",
                    },
                    "fields": {
                        "block_number": swap.block_number,
                        "log_index": swap.log_index,
                        "amount_in": swap.amount_in,  # Will be converted to string by write_points
                        "amount_out": swap.amount_out,  # Will be converted to string by write_points
                        "price_impact": swap.price_impact or 0.0,
                    }
                }
                points.append(point)
                
            # write_points handles large integers safely
            self.db_client.write_points(points)
            logger.debug(f"Stored {len(swaps)} DEX swaps")
            
        except Exception as e:
            logger.error(f"Error storing DEX swaps: {e}")
            
    def store_liquidity_events(self, events: List[LiquidityEvent]):
        """Store liquidity events to database."""
        if not self.db_client or not events:
            return
            
        try:
            points = []
            for event in events:
                point = {
                    "measurement": "dex_liquidity",
                    "time": event.block_timestamp,
                    "tags": {
                        "tx_hash": event.tx_hash,
                        "dex_address": event.dex_address,
                        "event_type": event.event_type,
                        "provider": event.provider,
                        "token0": event.token0,
                        "token1": event.token1,
                        "pair_address": event.pair_address,
                    },
                    "fields": {
                        "block_number": event.block_number,
                        "log_index": event.log_index,
                        "amount0": event.amount0,  # Will be converted to string by write_points
                        "amount1": event.amount1,  # Will be converted to string by write_points
                        "liquidity_delta": event.liquidity_delta or 0,
                        "total_liquidity": event.total_liquidity or 0,
                    }
                }
                points.append(point)
                
            # write_points handles large integers safely
            self.db_client.write_points(points)
            logger.debug(f"Stored {len(events)} liquidity events")
            
        except Exception as e:
            logger.error(f"Error storing liquidity events: {e}")
            
    async def calculate_dex_metrics(self, pair_address: str, time_period: str = "24h") -> Dict[str, Any]:
        """Calculate DEX metrics for a trading pair."""
        if not self.db_client:
            return {}
            
        try:
            # Calculate trading volume, number of swaps, etc.
            metrics = {
                "total_swaps": 0,
                "total_volume_in": 0,
                "total_volume_out": 0,
                "unique_traders": 0,
                "average_swap_size": 0,
                "liquidity_events": 0,
                "net_liquidity_change": 0,
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating DEX metrics: {e}")
            return {}


async def test_dex_analytics():
    """Test the DEX analytics module."""
    from core.config import Config
    from core.blockchain_client import BlockchainClient
    from core.influxdb_client import BlockchainInfluxDB
    
    config = Config()
    blockchain_client = BlockchainClient(config)
    
    db_client = None
    if config.influxdb_token:
        db_client = BlockchainInfluxDB(config)
        await db_client.connect()
    
    dex_analytics = DEXAnalytics(blockchain_client, db_client, config)
    
    # Test with recent blocks
    try:
        await blockchain_client.connect()
        latest_block = await blockchain_client.get_latest_block_number()
        
        if latest_block:
            test_block = latest_block - 5
            block_data = await blockchain_client.get_block(test_block, include_transactions=True)
            
            if block_data and 'transactions' in block_data:
                print(f"Testing DEX analytics with block {test_block}")
                
                for tx in block_data['transactions'][:5]:
                    if isinstance(tx, dict):
                        receipt = await blockchain_client.get_transaction_receipt(tx['hash'])
                        if receipt and receipt.get('logs'):
                            swaps, liquidity_events = await dex_analytics.analyze_dex_logs(
                                tx, receipt, datetime.now()
                            )
                            
                            if swaps:
                                print(f"Found {len(swaps)} DEX swaps in tx {tx['hash']}")
                                for swap in swaps:
                                    print(f"  {swap.dex_type}: {swap.amount_in} {swap.token_in[:8]}... -> {swap.amount_out} {swap.token_out[:8]}...")
                                
                                if db_client:
                                    dex_analytics.store_swaps(swaps)
                                    
                            if liquidity_events:
                                print(f"Found {len(liquidity_events)} liquidity events in tx {tx['hash']}")
                                if db_client:
                                    dex_analytics.store_liquidity_events(liquidity_events)
            
    except Exception as e:
        print(f"Test error: {e}")
    
    finally:
        if db_client:
            await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_dex_analytics())