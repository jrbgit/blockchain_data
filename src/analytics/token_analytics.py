"""
Token Analytics Module
Tracks ERC20, ERC721, and ERC1155 token transfers and analytics.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
from web3.datastructures import AttributeDict
from hexbytes import HexBytes
from influxdb_client import Point

logger = logging.getLogger(__name__)


@dataclass
class TokenTransfer:
    """Represents a token transfer event."""
    tx_hash: str
    block_number: int
    block_timestamp: datetime
    log_index: int
    token_address: str
    token_type: str  # 'ERC20', 'ERC721', 'ERC1155'
    from_address: str
    to_address: str
    value: Optional[int] = None  # For ERC20 and single ERC1155
    token_id: Optional[int] = None  # For ERC721 and ERC1155
    values: Optional[List[int]] = None  # For batch ERC1155 transfers
    token_ids: Optional[List[int]] = None  # For batch ERC1155 transfers


@dataclass
class TokenInfo:
    """Token contract information."""
    address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    decimals: Optional[int] = None
    total_supply: Optional[int] = None
    token_type: str = "ERC20"


class TokenAnalytics:
    """Handles token transfer analysis and tracking."""
    
    # Standard ERC20 Transfer event signature
    ERC20_TRANSFER_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    # ERC721 Transfer event signature (same as ERC20)
    ERC721_TRANSFER_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    # ERC1155 Transfer signatures
    ERC1155_TRANSFER_SINGLE_SIGNATURE = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
    ERC1155_TRANSFER_BATCH_SIGNATURE = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
    
    def __init__(self, blockchain_client, db_client, config):
        self.blockchain_client = blockchain_client
        self.db_client = db_client
        self.config = config
        self.token_cache: Dict[str, TokenInfo] = {}
        
    async def analyze_transaction_logs(self, tx_data: Dict[str, Any], receipt: Dict[str, Any], 
                                     block_timestamp: datetime) -> List[TokenTransfer]:
        """Analyze transaction logs for token transfers."""
        transfers = []
        
        if not receipt or 'logs' not in receipt:
            return transfers
            
        for log in receipt['logs']:
            try:
                if not log.get('topics'):
                    continue
                    
                topic0 = log['topics'][0] if isinstance(log['topics'][0], str) else log['topics'][0].hex()
                
                if topic0 == self.ERC20_TRANSFER_SIGNATURE:
                    # Could be ERC20 or ERC721
                    transfer = await self._parse_erc20_721_transfer(log, tx_data, block_timestamp)
                    if transfer:
                        transfers.append(transfer)
                        
                elif topic0 == self.ERC1155_TRANSFER_SINGLE_SIGNATURE:
                    transfer = await self._parse_erc1155_single_transfer(log, tx_data, block_timestamp)
                    if transfer:
                        transfers.append(transfer)
                        
                elif topic0 == self.ERC1155_TRANSFER_BATCH_SIGNATURE:
                    batch_transfers = await self._parse_erc1155_batch_transfer(log, tx_data, block_timestamp)
                    transfers.extend(batch_transfers)
                    
            except Exception as e:
                logger.debug(f"Error parsing log in tx {tx_data.get('hash', 'unknown')}: {e}")
                
        return transfers
        
    async def _parse_erc20_721_transfer(self, log: Dict[str, Any], tx_data: Dict[str, Any], 
                                      block_timestamp: datetime) -> Optional[TokenTransfer]:
        """Parse ERC20 or ERC721 transfer event."""
        try:
            if len(log['topics']) < 3:
                return None
                
            token_address = log['address']
            from_address = self._address_from_topic(log['topics'][1])
            to_address = self._address_from_topic(log['topics'][2])
            
            # Determine if ERC20 or ERC721 by checking data length
            data = log.get('data', '0x')
            if data == '0x' or len(data) <= 2:
                # No data usually means ERC721 with tokenId in topics[3]
                token_type = "ERC721"
                token_id = int(log['topics'][3], 16) if len(log['topics']) > 3 else None
                value = 1  # ERC721 transfers are always 1 token
            else:
                # Has data, likely ERC20
                token_type = "ERC20"
                value = int(data, 16) if data != '0x' else 0
                token_id = None
                
            return TokenTransfer(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                token_address=token_address,
                token_type=token_type,
                from_address=from_address,
                to_address=to_address,
                value=value,
                token_id=token_id
            )
            
        except Exception as e:
            logger.debug(f"Error parsing ERC20/721 transfer: {e}")
            return None
            
    async def _parse_erc1155_single_transfer(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                                           block_timestamp: datetime) -> Optional[TokenTransfer]:
        """Parse ERC1155 single transfer event."""
        try:
            if len(log['topics']) < 4:
                return None
                
            token_address = log['address']
            operator = self._address_from_topic(log['topics'][1])
            from_address = self._address_from_topic(log['topics'][2])
            to_address = self._address_from_topic(log['topics'][3])
            
            # Parse data for id and value
            data = log.get('data', '0x')
            if len(data) < 130:  # Should have at least 64 bytes (32 for id, 32 for value)
                return None
                
            token_id = int(data[2:66], 16)  # First 32 bytes
            value = int(data[66:130], 16)   # Second 32 bytes
            
            return TokenTransfer(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                token_address=token_address,
                token_type="ERC1155",
                from_address=from_address,
                to_address=to_address,
                value=value,
                token_id=token_id
            )
            
        except Exception as e:
            logger.debug(f"Error parsing ERC1155 single transfer: {e}")
            return None
            
    async def _parse_erc1155_batch_transfer(self, log: Dict[str, Any], tx_data: Dict[str, Any],
                                          block_timestamp: datetime) -> List[TokenTransfer]:
        """Parse ERC1155 batch transfer event."""
        transfers = []
        
        try:
            if len(log['topics']) < 4:
                return transfers
                
            token_address = log['address']
            operator = self._address_from_topic(log['topics'][1])
            from_address = self._address_from_topic(log['topics'][2])
            to_address = self._address_from_topic(log['topics'][3])
            
            # Parse batch data - this is complex as it contains dynamic arrays
            data = log.get('data', '0x')
            if len(data) < 130:
                return transfers
                
            # This is a simplified parser - in practice, you'd need a full ABI decoder
            # For now, we'll create a single transfer representing the batch
            return [TokenTransfer(
                tx_hash=tx_data['hash'],
                block_number=int(tx_data['blockNumber'], 16),
                block_timestamp=block_timestamp,
                log_index=int(log['logIndex'], 16),
                token_address=token_address,
                token_type="ERC1155_BATCH",
                from_address=from_address,
                to_address=to_address
            )]
            
        except Exception as e:
            logger.debug(f"Error parsing ERC1155 batch transfer: {e}")
            return transfers
            
    def _address_from_topic(self, topic: str) -> str:
        """Extract address from log topic."""
        if isinstance(topic, HexBytes):
            topic = topic.hex()
        # Remove '0x' and pad to get last 40 characters (20 bytes)
        addr = topic[-40:]
        return f"0x{addr}"
        
    async def get_token_info(self, token_address: str) -> Optional[TokenInfo]:
        """Get token contract information."""
        if token_address in self.token_cache:
            return self.token_cache[token_address]
            
        try:
            # Try to get token info from contract
            # This would require web3 contract calls - simplified for now
            token_info = TokenInfo(
                address=token_address,
                symbol=None,  # Would fetch from contract.functions.symbol().call()
                name=None,    # Would fetch from contract.functions.name().call()  
                decimals=None, # Would fetch from contract.functions.decimals().call()
                total_supply=None,
                token_type="ERC20"  # Default assumption
            )
            
            self.token_cache[token_address] = token_info
            return token_info
            
        except Exception as e:
            logger.debug(f"Error getting token info for {token_address}: {e}")
            return None
            
    def store_token_transfers(self, transfers: List[TokenTransfer]):
        """Store token transfers to database."""
        if not self.db_client or not transfers:
            return
            
        try:
            points = []
            for transfer in transfers:
                # Always convert token values to strings to maintain InfluxDB field type consistency
                # This prevents "field type conflict" errors when mixing int and string values
                value = transfer.value or 0
                token_id = transfer.token_id or 0
                
                # Always store as strings to ensure consistent field types in InfluxDB
                value_field = str(value)
                token_id_field = str(token_id)
                
                point = Point("token_transfers") \
                    .tag("tx_hash", transfer.tx_hash) \
                    .tag("token_address", transfer.token_address) \
                    .tag("token_type", transfer.token_type) \
                    .tag("from_address", transfer.from_address) \
                    .tag("to_address", transfer.to_address) \
                    .field("block_number", transfer.block_number) \
                    .field("log_index", transfer.log_index) \
                    .field("value", value_field) \
                    .field("token_id", token_id_field) \
                    .time(transfer.block_timestamp)
                points.append(point)
                
            self.db_client.write_batch(points)
            logger.debug(f"Stored {len(transfers)} token transfers")
            
        except Exception as e:
            logger.error(f"Error storing token transfers: {e}")
            
    async def calculate_token_metrics(self, token_address: str, 
                                    time_period: str = "24h") -> Dict[str, Any]:
        """Calculate token metrics for a given time period."""
        if not self.db_client:
            return {}
            
        try:
            # Query token transfers for the time period
            query = f'''
                FROM(bucket: "{self.db_client.bucket}")
                |> range(start: -{time_period})
                |> filter(fn: (r) => r._measurement == "token_transfers")
                |> filter(fn: (r) => r.token_address == "{token_address}")
            '''
            
            # This would execute the query and calculate metrics
            # Simplified for now
            metrics = {
                "total_transfers": 0,
                "unique_senders": 0,
                "unique_receivers": 0,
                "total_volume": 0,
                "average_transfer_size": 0,
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating token metrics: {e}")
            return {}


async def test_token_analytics():
    """Test the token analytics module."""
    from core.config import Config
    from core.blockchain_client import BlockchainClient
    from core.influxdb_client import BlockchainInfluxDB
    
    config = Config()
    blockchain_client = BlockchainClient(config)
    
    db_client = None
    if config.influxdb_token:
        db_client = BlockchainInfluxDB(config)
        await db_client.connect()
    
    analytics = TokenAnalytics(blockchain_client, db_client, config)
    
    # Test with a recent block that might have token transfers
    try:
        await blockchain_client.connect()
        latest_block = await blockchain_client.get_latest_block_number()
        
        if latest_block:
            test_block = latest_block - 10  # Test with a recent block
            block_data = await blockchain_client.get_block(test_block, include_transactions=True)
            
            if block_data and 'transactions' in block_data:
                print(f"Testing token analytics with block {test_block}")
                
                for tx in block_data['transactions'][:3]:  # Test first 3 transactions
                    if isinstance(tx, dict):
                        receipt = await blockchain_client.get_transaction_receipt(tx['hash'])
                        if receipt:
                            transfers = await analytics.analyze_transaction_logs(
                                tx, receipt, datetime.now()
                            )
                            
                            if transfers:
                                print(f"Found {len(transfers)} token transfers in tx {tx['hash']}")
                                for transfer in transfers:
                                    print(f"  {transfer.token_type}: {transfer.value} from {transfer.from_address[:8]}... to {transfer.to_address[:8]}...")
                                
                                if db_client:
                                    analytics.store_token_transfers(transfers)
            
    except Exception as e:
        print(f"Test error: {e}")
    
    finally:
        if db_client:
            await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_token_analytics())