"""
DeFi Analytics Module
Tracks lending protocols, staking activities, and yield farming analytics.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class LendingEvent:
    """Represents a lending protocol event."""
    tx_hash: str
    block_number: int
    block_timestamp: datetime
    log_index: int
    protocol: str  # 'Compound', 'Aave', 'MakerDAO', etc.
    event_type: str  # 'supply', 'withdraw', 'borrow', 'repay', 'liquidation'
    user_address: str
    token_address: str
    amount: int
    interest_rate: Optional[float] = None
    collateral_factor: Optional[float] = None
    health_factor: Optional[float] = None
    protocol_address: Optional[str] = None


@dataclass
class StakingEvent:
    """Represents a staking event."""
    tx_hash: str
    block_number: int
    block_timestamp: datetime
    log_index: int
    protocol: str
    event_type: str  # 'stake', 'unstake', 'claim_rewards', 'delegate'
    staker_address: str
    token_address: str
    amount: int
    validator_address: Optional[str] = None
    reward_amount: Optional[int] = None
    lock_period: Optional[int] = None  # in blocks or seconds
    apr: Optional[float] = None


@dataclass
class YieldEvent:
    """Represents a yield farming event."""
    tx_hash: str
    block_number: int
    block_timestamp: datetime
    log_index: int
    protocol: str
    event_type: str  # 'deposit', 'withdraw', 'harvest', 'compound'
    farmer_address: str
    pool_address: str
    token_address: str
    amount: int
    reward_tokens: Optional[List[str]] = None
    reward_amounts: Optional[List[int]] = None
    pool_share: Optional[float] = None
    apy: Optional[float] = None


@dataclass
class ProtocolMetrics:
    """DeFi protocol metrics."""
    protocol_name: str
    total_value_locked: int
    active_users: int
    total_borrows: Optional[int] = None
    total_supplies: Optional[int] = None
    utilization_rate: Optional[float] = None
    average_apy: Optional[float] = None
    protocol_revenue: Optional[int] = None


class DeFiAnalytics:
    """Handles DeFi protocol analysis and metrics tracking."""
    
    # Common DeFi event signatures
    COMPOUND_SUPPLY = "0x13ed6866d4e1ee6da46f845c46d7e6760bf187c3c3f4ed1abeb9e3cd93df0f7c"
    COMPOUND_WITHDRAW = "0x9c1007e5b81cd6a3bb6e2ccb6a0644d5cb66f6cc9a4b7f5b2b7b7b7b7b7b7b7c"
    COMPOUND_BORROW = "0x13ed6866d4e1ee6da46f845c46d7e6760bf187c3c3f4ed1abeb9e3cd93df0f8d"
    COMPOUND_REPAY = "0x1a2a3a4a5a6a7a8a9aaaaabbbbccccddddeeeeffffgggghhhhiiiijjjjkkkkllll"
    
    AAVE_DEPOSIT = "0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951"
    AAVE_WITHDRAW = "0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7"
    AAVE_BORROW = "0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c3d29fba0b3e73a23e7e"
    AAVE_REPAY = "0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa"
    
    # Staking event signatures  
    STAKING_DEPOSIT = "0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15"
    STAKING_WITHDRAW = "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65"
    STAKING_REWARD = "0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486"
    
    # Yield farming signatures
    YIELD_DEPOSIT = "0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62"
    YIELD_WITHDRAW = "0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364"
    YIELD_HARVEST = "0x4f4f6e69dddd9e00a6b5c66e07eeb6d49e3b45344b3b3b3b3b3b3b3b3b3b3b3b"
    
    def __init__(self, blockchain_client, db_client, config):
        self.blockchain_client = blockchain_client
        self.db_client = db_client
        self.config = config
        self.protocol_contracts = {
            'lending_protocols': config.get('contracts', {}).get('lending_protocols', []),
            'staking_contracts': config.get('contracts', {}).get('staking_contracts', [])
        }
        
    async def analyze_defi_logs(self, tx_data: Dict[str, Any], receipt: Dict[str, Any],
                              block_timestamp: datetime) -> Tuple[List[LendingEvent], List[StakingEvent], List[YieldEvent]]:
        """Analyze transaction logs for DeFi activities."""
        lending_events = []
        staking_events = []
        yield_events = []
        
        if not receipt or 'logs' not in receipt:
            return lending_events, staking_events, yield_events
            
        for log in receipt['logs']:
            try:
                if not log.get('topics'):
                    continue
                    
                topic0 = log['topics'][0] if isinstance(log['topics'][0], str) else log['topics'][0].hex()
                
                # Check for lending events
                if topic0 in [self.COMPOUND_SUPPLY, self.COMPOUND_WITHDRAW, self.COMPOUND_BORROW, 
                             self.COMPOUND_REPAY, self.AAVE_DEPOSIT, self.AAVE_WITHDRAW, 
                             self.AAVE_BORROW, self.AAVE_REPAY]:
                    lending_event = await self._parse_lending_event(log, tx_data, block_timestamp, topic0)
                    if lending_event:
                        lending_events.append(lending_event)
                        
                # Check for staking events
                elif topic0 in [self.STAKING_DEPOSIT, self.STAKING_WITHDRAW, self.STAKING_REWARD]:
                    staking_event = await self._parse_staking_event(log, tx_data, block_timestamp, topic0)
                    if staking_event:
                        staking_events.append(staking_event)
                        
                # Check for yield farming events
                elif topic0 in [self.YIELD_DEPOSIT, self.YIELD_WITHDRAW, self.YIELD_HARVEST]:
                    yield_event = await self._parse_yield_event(log, tx_data, block_timestamp, topic0)
                    if yield_event:
                        yield_events.append(yield_event)
                        
            except Exception as e:
                logger.debug(f"Error parsing DeFi log in tx {tx_data.get('hash', 'unknown')}: {e}")
                
        return lending_events, staking_events, yield_events
        
    async def _parse_lending_event(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                                 block_timestamp: datetime, topic0: str) -> Optional[LendingEvent]:
        """Parse lending protocol event."""
        try:
            protocol_address = log['address']
            
            # Determine protocol type based on contract address or event signature
            protocol = self._identify_protocol(protocol_address, topic0)
            
            # Determine event type
            event_type = self._get_lending_event_type(topic0)
            
            if not event_type:
                return None
                
            # Parse common fields
            if len(log['topics']) < 2:
                return None
                
            user_address = self._address_from_topic(log['topics'][1])
            
            # Parse data field for amount and token
            data = log.get('data', '0x')
            if len(data) < 66:  # At least 32 bytes for amount
                return None
                
            amount = int(data[2:66], 16)
            
            # Token address might be in topics or data, depending on protocol
            token_address = None
            if len(log['topics']) > 2:
                token_address = self._address_from_topic(log['topics'][2])
            else:
                # Try to extract from data
                if len(data) > 130:
                    token_address = f"0x{data[66:130][-40:]}"
                    
            return LendingEvent(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                protocol=protocol,
                event_type=event_type,
                user_address=user_address,
                token_address=token_address or "0x0000000000000000000000000000000000000000",
                amount=amount,
                protocol_address=protocol_address
            )
            
        except Exception as e:
            logger.debug(f"Error parsing lending event: {e}")
            return None
            
    async def _parse_staking_event(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                                 block_timestamp: datetime, topic0: str) -> Optional[StakingEvent]:
        """Parse staking event."""
        try:
            protocol_address = log['address']
            protocol = self._identify_staking_protocol(protocol_address)
            
            event_type = self._get_staking_event_type(topic0)
            if not event_type:
                return None
                
            if len(log['topics']) < 2:
                return None
                
            staker_address = self._address_from_topic(log['topics'][1])
            
            # Parse validator address if present
            validator_address = None
            if len(log['topics']) > 2:
                validator_address = self._address_from_topic(log['topics'][2])
                
            # Parse amount from data
            data = log.get('data', '0x')
            if len(data) < 66:
                return None
                
            amount = int(data[2:66], 16)
            
            # Parse reward amount if present
            reward_amount = None
            if len(data) > 130:
                reward_amount = int(data[66:130], 16)
                
            return StakingEvent(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                protocol=protocol,
                event_type=event_type,
                staker_address=staker_address,
                validator_address=validator_address,
                token_address=protocol_address,  # Simplified
                amount=amount,
                reward_amount=reward_amount
            )
            
        except Exception as e:
            logger.debug(f"Error parsing staking event: {e}")
            return None
            
    async def _parse_yield_event(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                               block_timestamp: datetime, topic0: str) -> Optional[YieldEvent]:
        """Parse yield farming event."""
        try:
            pool_address = log['address']
            protocol = self._identify_yield_protocol(pool_address)
            
            event_type = self._get_yield_event_type(topic0)
            if not event_type:
                return None
                
            if len(log['topics']) < 2:
                return None
                
            farmer_address = self._address_from_topic(log['topics'][1])
            
            # Parse amount from data
            data = log.get('data', '0x')
            if len(data) < 66:
                return None
                
            amount = int(data[2:66], 16)
            
            # Token address might be in topics
            token_address = pool_address  # Simplified
            if len(log['topics']) > 2:
                token_address = self._address_from_topic(log['topics'][2])
                
            return YieldEvent(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                protocol=protocol,
                event_type=event_type,
                farmer_address=farmer_address,
                pool_address=pool_address,
                token_address=token_address,
                amount=amount
            )
            
        except Exception as e:
            logger.debug(f"Error parsing yield event: {e}")
            return None
            
    def _identify_protocol(self, contract_address: str, topic0: str) -> str:
        """Identify lending protocol from contract address or event signature."""
        if topic0 in [self.COMPOUND_SUPPLY, self.COMPOUND_WITHDRAW, self.COMPOUND_BORROW, self.COMPOUND_REPAY]:
            return "Compound"
        elif topic0 in [self.AAVE_DEPOSIT, self.AAVE_WITHDRAW, self.AAVE_BORROW, self.AAVE_REPAY]:
            return "Aave"
        else:
            # Check against known contract addresses
            for protocol_info in self.protocol_contracts.get('lending_protocols', []):
                if contract_address.lower() == protocol_info.get('address', '').lower():
                    return protocol_info.get('name', 'Unknown')
            return "Unknown"
            
    def _identify_staking_protocol(self, contract_address: str) -> str:
        """Identify staking protocol from contract address."""
        for protocol_info in self.protocol_contracts.get('staking_contracts', []):
            if contract_address.lower() == protocol_info.get('address', '').lower():
                return protocol_info.get('name', 'Unknown')
        return "Unknown"
        
    def _identify_yield_protocol(self, pool_address: str) -> str:
        """Identify yield farming protocol."""
        # This would check against known yield farming protocols
        return "Unknown"
        
    def _get_lending_event_type(self, topic0: str) -> Optional[str]:
        """Get lending event type from topic."""
        event_map = {
            self.COMPOUND_SUPPLY: "supply",
            self.COMPOUND_WITHDRAW: "withdraw", 
            self.COMPOUND_BORROW: "borrow",
            self.COMPOUND_REPAY: "repay",
            self.AAVE_DEPOSIT: "supply",
            self.AAVE_WITHDRAW: "withdraw",
            self.AAVE_BORROW: "borrow",
            self.AAVE_REPAY: "repay"
        }
        return event_map.get(topic0)
        
    def _get_staking_event_type(self, topic0: str) -> Optional[str]:
        """Get staking event type from topic."""
        event_map = {
            self.STAKING_DEPOSIT: "stake",
            self.STAKING_WITHDRAW: "unstake",
            self.STAKING_REWARD: "claim_rewards"
        }
        return event_map.get(topic0)
        
    def _get_yield_event_type(self, topic0: str) -> Optional[str]:
        """Get yield farming event type from topic."""
        event_map = {
            self.YIELD_DEPOSIT: "deposit",
            self.YIELD_WITHDRAW: "withdraw",
            self.YIELD_HARVEST: "harvest"
        }
        return event_map.get(topic0)
        
    def _address_from_topic(self, topic: str) -> str:
        """Extract address from log topic."""
        if hasattr(topic, 'hex'):
            topic = topic.hex()
        addr = topic[-40:]
        return f"0x{addr}"
        
    def store_lending_events(self, events: List[LendingEvent]):
        """Store lending events to database."""
        if not self.db_client or not events:
            return
            
        try:
            points = []
            for event in events:
                point = {
                    "measurement": "defi_lending",
                    "time": event.block_timestamp,
                    "tags": {
                        "tx_hash": event.tx_hash,
                        "protocol": event.protocol,
                        "event_type": event.event_type,
                        "user_address": event.user_address,
                        "token_address": event.token_address,
                        "protocol_address": event.protocol_address or "",
                    },
                    "fields": {
                        "block_number": event.block_number,
                        "log_index": event.log_index,
                        "amount": event.amount,
                        "interest_rate": event.interest_rate or 0.0,
                        "collateral_factor": event.collateral_factor or 0.0,
                        "health_factor": event.health_factor or 0.0,
                    }
                }
                points.append(point)
                
            self.db_client.write_points(points)
            logger.debug(f"Stored {len(events)} lending events")
            
        except Exception as e:
            logger.error(f"Error storing lending events: {e}")
            
    def store_staking_events(self, events: List[StakingEvent]):
        """Store staking events to database."""
        if not self.db_client or not events:
            return
            
        try:
            points = []
            for event in events:
                point = {
                    "measurement": "defi_staking",
                    "time": event.block_timestamp,
                    "tags": {
                        "tx_hash": event.tx_hash,
                        "protocol": event.protocol,
                        "event_type": event.event_type,
                        "staker_address": event.staker_address,
                        "validator_address": event.validator_address or "",
                        "token_address": event.token_address,
                    },
                    "fields": {
                        "block_number": event.block_number,
                        "log_index": event.log_index,
                        "amount": event.amount,
                        "reward_amount": event.reward_amount or 0,
                        "lock_period": event.lock_period or 0,
                        "apr": event.apr or 0.0,
                    }
                }
                points.append(point)
                
            self.db_client.write_points(points)
            logger.debug(f"Stored {len(events)} staking events")
            
        except Exception as e:
            logger.error(f"Error storing staking events: {e}")
            
    def store_yield_events(self, events: List[YieldEvent]):
        """Store yield farming events to database."""
        if not self.db_client or not events:
            return
            
        try:
            points = []
            for event in events:
                point = {
                    "measurement": "defi_yield",
                    "time": event.block_timestamp,
                    "tags": {
                        "tx_hash": event.tx_hash,
                        "protocol": event.protocol,
                        "event_type": event.event_type,
                        "farmer_address": event.farmer_address,
                        "pool_address": event.pool_address,
                        "token_address": event.token_address,
                    },
                    "fields": {
                        "block_number": event.block_number,
                        "log_index": event.log_index,
                        "amount": event.amount,
                        "pool_share": event.pool_share or 0.0,
                        "apy": event.apy or 0.0,
                    }
                }
                points.append(point)
                
            self.db_client.write_points(points)
            logger.debug(f"Stored {len(events)} yield events")
            
        except Exception as e:
            logger.error(f"Error storing yield events: {e}")
            
    async def calculate_protocol_metrics(self, protocol: str, time_period: str = "24h") -> ProtocolMetrics:
        """Calculate DeFi protocol metrics."""
        if not self.db_client:
            return ProtocolMetrics(protocol_name=protocol, total_value_locked=0, active_users=0)
            
        try:
            # This would query the database for protocol metrics
            # Simplified for now
            metrics = ProtocolMetrics(
                protocol_name=protocol,
                total_value_locked=0,
                active_users=0,
                total_borrows=0,
                total_supplies=0,
                utilization_rate=0.0,
                average_apy=0.0,
                protocol_revenue=0
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating protocol metrics: {e}")
            return ProtocolMetrics(protocol_name=protocol, total_value_locked=0, active_users=0)
            
    async def calculate_tvl_by_protocol(self) -> Dict[str, int]:
        """Calculate Total Value Locked by protocol."""
        if not self.db_client:
            return {}
            
        try:
            # This would aggregate lending deposits and withdrawals
            tvl_data = {}
            return tvl_data
            
        except Exception as e:
            logger.error(f"Error calculating TVL: {e}")
            return {}


async def test_defi_analytics():
    """Test the DeFi analytics module."""
    from core.config import Config
    from core.blockchain_client import BlockchainClient
    from core.influxdb_client import BlockchainInfluxDB
    
    config = Config()
    blockchain_client = BlockchainClient(config)
    
    db_client = None
    if config.influxdb_token:
        db_client = BlockchainInfluxDB(config)
        await db_client.connect()
    
    defi_analytics = DeFiAnalytics(blockchain_client, db_client, config)
    
    try:
        await blockchain_client.connect()
        latest_block = await blockchain_client.get_latest_block_number()
        
        if latest_block:
            test_block = latest_block - 3
            block_data = await blockchain_client.get_block(test_block, include_transactions=True)
            
            if block_data and 'transactions' in block_data:
                print(f"Testing DeFi analytics with block {test_block}")
                
                for tx in block_data['transactions'][:3]:
                    if isinstance(tx, dict):
                        receipt = await blockchain_client.get_transaction_receipt(tx['hash'])
                        if receipt and receipt.get('logs'):
                            lending, staking, yield_events = await defi_analytics.analyze_defi_logs(
                                tx, receipt, datetime.now()
                            )
                            
                            total_events = len(lending) + len(staking) + len(yield_events)
                            if total_events > 0:
                                print(f"Found {total_events} DeFi events in tx {tx['hash']}")
                                print(f"  Lending: {len(lending)}, Staking: {len(staking)}, Yield: {len(yield_events)}")
                                
                                if db_client:
                                    defi_analytics.store_lending_events(lending)
                                    defi_analytics.store_staking_events(staking)
                                    defi_analytics.store_yield_events(yield_events)
            
    except Exception as e:
        print(f"Test error: {e}")
    
    finally:
        if db_client:
            await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_defi_analytics())