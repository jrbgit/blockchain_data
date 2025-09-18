"""
Chain-Specific Data Processors

This module contains specialized processors for different blockchain networks,
handling chain-specific logic, protocols, and data extraction patterns.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Union
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
import json
import re

from web3 import Web3
from web3.types import BlockData, TxData, LogReceipt

from ..core.config import Config
from ..core.multichain_client import MultiChainClient
from ..core.multichain_influxdb_client import MultiChainInfluxDB

logger = logging.getLogger(__name__)


@dataclass
class ProcessedTransaction:
    """Standardized transaction data across chains"""
    chain_id: str
    block_number: int
    transaction_hash: str
    from_address: str
    to_address: Optional[str]
    value: str  # Native currency value as string
    gas_used: int
    gas_price: int
    transaction_fee: str
    status: str
    transaction_type: str
    input_data_size: int
    timestamp: datetime
    
    # Chain-specific additional data
    extras: Dict[str, Any]


@dataclass
class ProcessedEvent:
    """Standardized event/log data across chains"""
    chain_id: str
    block_number: int
    transaction_hash: str
    log_index: int
    contract_address: str
    event_signature: str
    topics: List[str]
    data: str
    decoded_data: Optional[Dict[str, Any]]
    timestamp: datetime


@dataclass 
class ProcessedTokenTransfer:
    """Standardized token transfer data"""
    chain_id: str
    block_number: int
    transaction_hash: str
    log_index: int
    token_address: str
    token_standard: str  # ERC20, ERC721, ERC1155
    from_address: str
    to_address: str
    amount: str
    token_id: Optional[str]  # For NFTs
    token_symbol: Optional[str]
    token_name: Optional[str]
    token_decimals: Optional[int]
    timestamp: datetime


class BaseChainProcessor(ABC):
    """Abstract base class for chain-specific processors"""
    
    def __init__(self, chain_id: str, config: Config, multichain_client: MultiChainClient):
        self.chain_id = chain_id
        self.config = config
        self.client = multichain_client
        self.chain_config = config.chains.get(chain_id, {})
        self.chain_name = self.chain_config.get('name', chain_id)
        
        # Token contract signatures for events
        self.erc20_transfer_signature = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        self.erc721_transfer_signature = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        self.erc1155_single_signature = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
        self.erc1155_batch_signature = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
        
    @abstractmethod
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block and return processed data"""
        pass
    
    @abstractmethod
    async def process_transaction(self, tx_data: Dict[str, Any], block_data: Dict[str, Any]) -> ProcessedTransaction:
        """Process a transaction and return standardized data"""
        pass
    
    @abstractmethod
    async def process_events(self, tx_receipt: Optional[Dict[str, Any]], 
                           block_data: Dict[str, Any]) -> List[ProcessedEvent]:
        """Process transaction events/logs"""
        pass
    
    async def process_token_transfers(self, events: List[ProcessedEvent]) -> List[ProcessedTokenTransfer]:
        """Extract token transfers from events (default EVM implementation)"""
        transfers = []
        
        for event in events:
            try:
                # ERC-20 Transfer
                if (event.event_signature == self.erc20_transfer_signature and 
                    len(event.topics) == 3):  # Transfer(from, to, value)
                    
                    transfer = await self._process_erc20_transfer(event)
                    if transfer:
                        transfers.append(transfer)
                
                # ERC-721 Transfer (same signature as ERC-20 but different topic structure)
                elif (event.event_signature == self.erc721_transfer_signature and 
                      len(event.topics) == 4):  # Transfer(from, to, tokenId)
                    
                    transfer = await self._process_erc721_transfer(event)
                    if transfer:
                        transfers.append(transfer)
                
                # ERC-1155 Transfers
                elif event.event_signature == self.erc1155_single_signature:
                    transfer = await self._process_erc1155_single_transfer(event)
                    if transfer:
                        transfers.append(transfer)
                
                elif event.event_signature == self.erc1155_batch_signature:
                    batch_transfers = await self._process_erc1155_batch_transfer(event)
                    transfers.extend(batch_transfers)
                    
            except Exception as e:
                logger.error(f"Error processing token transfer from event: {e}")
                continue
        
        return transfers
    
    async def _process_erc20_transfer(self, event: ProcessedEvent) -> Optional[ProcessedTokenTransfer]:
        """Process ERC-20 transfer event"""
        try:
            # Decode topics: [signature, from, to]
            from_address = "0x" + event.topics[1][-40:]  # Last 40 chars (20 bytes)
            to_address = "0x" + event.topics[2][-40:]
            
            # Decode data (value)
            value = int(event.data, 16) if event.data and event.data != "0x" else 0
            
            # Try to get token info
            token_info = await self._get_token_info(event.contract_address)
            
            return ProcessedTokenTransfer(
                chain_id=self.chain_id,
                block_number=event.block_number,
                transaction_hash=event.transaction_hash,
                log_index=event.log_index,
                token_address=event.contract_address,
                token_standard="ERC20",
                from_address=from_address,
                to_address=to_address,
                amount=str(value),
                token_id=None,
                token_symbol=token_info.get('symbol'),
                token_name=token_info.get('name'),
                token_decimals=token_info.get('decimals'),
                timestamp=event.timestamp
            )
            
        except Exception as e:
            logger.error(f"Error processing ERC-20 transfer: {e}")
            return None
    
    async def _process_erc721_transfer(self, event: ProcessedEvent) -> Optional[ProcessedTokenTransfer]:
        """Process ERC-721 transfer event"""
        try:
            # Decode topics: [signature, from, to, tokenId]
            from_address = "0x" + event.topics[1][-40:]
            to_address = "0x" + event.topics[2][-40:]
            token_id = str(int(event.topics[3], 16))
            
            # Try to get token info
            token_info = await self._get_token_info(event.contract_address)
            
            return ProcessedTokenTransfer(
                chain_id=self.chain_id,
                block_number=event.block_number,
                transaction_hash=event.transaction_hash,
                log_index=event.log_index,
                token_address=event.contract_address,
                token_standard="ERC721",
                from_address=from_address,
                to_address=to_address,
                amount="1",  # NFTs are always quantity 1
                token_id=token_id,
                token_symbol=token_info.get('symbol'),
                token_name=token_info.get('name'),
                token_decimals=None,
                timestamp=event.timestamp
            )
            
        except Exception as e:
            logger.error(f"Error processing ERC-721 transfer: {e}")
            return None
    
    async def _process_erc1155_single_transfer(self, event: ProcessedEvent) -> Optional[ProcessedTokenTransfer]:
        """Process ERC-1155 single transfer event"""
        try:
            # TransferSingle(operator, from, to, id, value)
            # Topics: [signature, operator, from, to]
            from_address = "0x" + event.topics[2][-40:]
            to_address = "0x" + event.topics[3][-40:]
            
            # Decode data: id (32 bytes) + value (32 bytes)
            if len(event.data) >= 130:  # 0x + 64 + 64 chars
                token_id = str(int(event.data[2:66], 16))  # First 32 bytes
                amount = str(int(event.data[66:130], 16))  # Second 32 bytes
            else:
                return None
            
            token_info = await self._get_token_info(event.contract_address)
            
            return ProcessedTokenTransfer(
                chain_id=self.chain_id,
                block_number=event.block_number,
                transaction_hash=event.transaction_hash,
                log_index=event.log_index,
                token_address=event.contract_address,
                token_standard="ERC1155",
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                token_id=token_id,
                token_symbol=token_info.get('symbol'),
                token_name=token_info.get('name'),
                token_decimals=None,
                timestamp=event.timestamp
            )
            
        except Exception as e:
            logger.error(f"Error processing ERC-1155 single transfer: {e}")
            return None
    
    async def _process_erc1155_batch_transfer(self, event: ProcessedEvent) -> List[ProcessedTokenTransfer]:
        """Process ERC-1155 batch transfer event"""
        # Implementation would be more complex, parsing array data
        # For now, return empty list
        return []
    
    async def _get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get token information (symbol, name, decimals) - should be cached"""
        # TODO: Implement token info caching and retrieval
        # This would involve calling the token contract's methods
        return {}


class EthereumProcessor(BaseChainProcessor):
    """Ethereum Mainnet specialized processor"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient):
        super().__init__("ethereum", config, multichain_client)
        
        # Ethereum-specific configurations
        self.supports_eip1559 = True
        self.known_protocols = {
            "uniswap_v2": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
            "uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
            "compound": "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B",
            "aave_v2": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
        }
    
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Ethereum block with EIP-1559 support"""
        
        processed = {
            "block_number": int(block_data.get("number", 0)),
            "timestamp": datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            "gas_limit": int(block_data.get("gasLimit", 0)),
            "gas_used": int(block_data.get("gasUsed", 0)),
            "transaction_count": len(block_data.get("transactions", [])),
            "size": int(block_data.get("size", 0)),
            "miner": block_data.get("miner", ""),
            "difficulty": str(block_data.get("difficulty", 0)),
            "total_difficulty": str(block_data.get("totalDifficulty", 0)),
        }
        
        # EIP-1559 specific fields
        if "baseFeePerGas" in block_data:
            processed["base_fee_per_gas"] = int(block_data["baseFeePerGas"])
        
        # Calculate gas utilization
        gas_limit = processed["gas_limit"]
        gas_used = processed["gas_used"]
        processed["gas_utilization"] = gas_used / gas_limit if gas_limit > 0 else 0
        
        # Calculate block time (if we have previous block)
        # This would require database lookup for previous block timestamp
        processed["block_time"] = 13.0  # Ethereum average, would calculate actual
        
        return processed
    
    async def process_transaction(self, tx_data: Dict[str, Any], block_data: Dict[str, Any]) -> ProcessedTransaction:
        """Process Ethereum transaction with EIP-1559 support"""
        
        # Determine transaction type
        tx_type = "transfer"
        to_address = tx_data.get("to")
        input_data = tx_data.get("input", "0x")
        
        if not to_address:  # Contract creation
            tx_type = "contract_creation"
        elif input_data and input_data != "0x":
            tx_type = "contract_call"
        
        # Calculate transaction fee
        gas_used = int(tx_data.get("gasUsed", 0))
        gas_price = int(tx_data.get("gasPrice", 0))
        
        # For EIP-1559 transactions
        effective_gas_price = gas_price
        if "effectiveGasPrice" in tx_data:
            effective_gas_price = int(tx_data["effectiveGasPrice"])
        
        transaction_fee = str(gas_used * effective_gas_price)
        
        # Get transaction status from receipt
        status = "success" if tx_data.get("status") == "0x1" else "failed"
        
        return ProcessedTransaction(
            chain_id=self.chain_id,
            block_number=int(block_data.get("number", 0)),
            transaction_hash=tx_data.get("hash", ""),
            from_address=tx_data.get("from", ""),
            to_address=to_address,
            value=str(int(tx_data.get("value", 0))),
            gas_used=gas_used,
            gas_price=gas_price,
            transaction_fee=transaction_fee,
            status=status,
            transaction_type=tx_type,
            input_data_size=len(input_data) // 2 - 1 if input_data.startswith("0x") else len(input_data) // 2,
            timestamp=datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            extras={
                "nonce": int(tx_data.get("nonce", 0)),
                "transaction_index": int(tx_data.get("transactionIndex", 0)),
                "effective_gas_price": effective_gas_price,
                "max_fee_per_gas": int(tx_data.get("maxFeePerGas", 0)) if "maxFeePerGas" in tx_data else None,
                "max_priority_fee_per_gas": int(tx_data.get("maxPriorityFeePerGas", 0)) if "maxPriorityFeePerGas" in tx_data else None,
                "type": tx_data.get("type", "0x0")
            }
        )
    
    async def process_events(self, tx_receipt: Optional[Dict[str, Any]], 
                           block_data: Dict[str, Any]) -> List[ProcessedEvent]:
        """Process Ethereum transaction events/logs"""
        events = []
        
        if not tx_receipt or "logs" not in tx_receipt:
            return events
        
        block_timestamp = datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc)
        
        for log in tx_receipt["logs"]:
            try:
                topics = log.get("topics", [])
                if not topics:
                    continue
                
                event = ProcessedEvent(
                    chain_id=self.chain_id,
                    block_number=int(log.get("blockNumber", 0)),
                    transaction_hash=log.get("transactionHash", ""),
                    log_index=int(log.get("logIndex", 0)),
                    contract_address=log.get("address", ""),
                    event_signature=topics[0] if topics else "",
                    topics=topics,
                    data=log.get("data", ""),
                    decoded_data=None,  # Would implement ABI decoding
                    timestamp=block_timestamp
                )
                
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing Ethereum event: {e}")
                continue
        
        return events


class PolygonProcessor(BaseChainProcessor):
    """Polygon (MATIC) specialized processor"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient):
        super().__init__("polygon", config, multichain_client)
        
        # Polygon-specific configurations
        self.supports_eip1559 = True
        self.pos_bridge_contracts = {
            "root_chain_manager": "0xA0c68C638235ee32657e8f720a23ceC1bFc77C77",
            "erc20_predicate": "0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf",
            "erc721_predicate": "0xE6F45A4F72bF6b6b6a2Bb00c8a8b6cC9e23CE9B1"
        }
        self.known_dexes = {
            "quickswap": "0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32",
            "sushiswap": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
            "1inch": "0x11111112542D85B3EF69AE05771c2dCCff4fAa26"
        }
    
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Polygon block with PoS-specific metrics"""
        
        processed = {
            "block_number": int(block_data.get("number", 0)),
            "timestamp": datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            "gas_limit": int(block_data.get("gasLimit", 0)),
            "gas_used": int(block_data.get("gasUsed", 0)),
            "transaction_count": len(block_data.get("transactions", [])),
            "size": int(block_data.get("size", 0)),
            "miner": block_data.get("miner", ""),  # Actually validator in PoS
        }
        
        # Polygon has faster block times (~2 seconds)
        processed["block_time"] = 2.0
        processed["gas_utilization"] = processed["gas_used"] / processed["gas_limit"] if processed["gas_limit"] > 0 else 0
        
        # EIP-1559 support
        if "baseFeePerGas" in block_data:
            processed["base_fee_per_gas"] = int(block_data["baseFeePerGas"])
        
        return processed
    
    async def process_transaction(self, tx_data: Dict[str, Any], block_data: Dict[str, Any]) -> ProcessedTransaction:
        """Process Polygon transaction (similar to Ethereum but with different gas economics)"""
        
        # Similar to Ethereum but with Polygon-specific considerations
        tx_type = "transfer"
        to_address = tx_data.get("to")
        input_data = tx_data.get("input", "0x")
        
        if not to_address:
            tx_type = "contract_creation"
        elif to_address.lower() in [addr.lower() for addr in self.pos_bridge_contracts.values()]:
            tx_type = "bridge_transaction"
        elif input_data and input_data != "0x":
            tx_type = "contract_call"
        
        gas_used = int(tx_data.get("gasUsed", 0))
        gas_price = int(tx_data.get("gasPrice", 0))
        effective_gas_price = int(tx_data.get("effectiveGasPrice", gas_price))
        
        return ProcessedTransaction(
            chain_id=self.chain_id,
            block_number=int(block_data.get("number", 0)),
            transaction_hash=tx_data.get("hash", ""),
            from_address=tx_data.get("from", ""),
            to_address=to_address,
            value=str(int(tx_data.get("value", 0))),
            gas_used=gas_used,
            gas_price=gas_price,
            transaction_fee=str(gas_used * effective_gas_price),
            status="success" if tx_data.get("status") == "0x1" else "failed",
            transaction_type=tx_type,
            input_data_size=len(input_data) // 2 - 1 if input_data.startswith("0x") else len(input_data) // 2,
            timestamp=datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            extras={
                "nonce": int(tx_data.get("nonce", 0)),
                "transaction_index": int(tx_data.get("transactionIndex", 0)),
                "effective_gas_price": effective_gas_price,
                "is_bridge_tx": tx_type == "bridge_transaction"
            }
        )
    
    async def process_events(self, tx_receipt: Optional[Dict[str, Any]], 
                           block_data: Dict[str, Any]) -> List[ProcessedEvent]:
        """Process Polygon events with bridge detection"""
        events = await super().process_events(tx_receipt, block_data)
        
        # Add Polygon-specific event processing (bridge events, etc.)
        for event in events:
            if event.contract_address.lower() in [addr.lower() for addr in self.pos_bridge_contracts.values()]:
                # This is a bridge-related event
                if event.decoded_data is None:
                    event.decoded_data = {}
                event.decoded_data["is_bridge_event"] = True
        
        return events


class BaseProcessor(BaseChainProcessor):
    """Base (Coinbase L2) specialized processor"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient):
        super().__init__("base", config, multichain_client)
        
        # Base-specific configurations
        self.supports_eip1559 = True
        self.l2_specific = True
        self.l1_bridge_contracts = {
            "l1_standard_bridge": "0x3154Cf16ccdb4C6d922629664174b904d80F2C35",
            "l2_standard_bridge": "0x4200000000000000000000000000000000000010"
        }
    
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Base block with L2-specific metrics"""
        
        processed = {
            "block_number": int(block_data.get("number", 0)),
            "timestamp": datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            "gas_limit": int(block_data.get("gasLimit", 0)),
            "gas_used": int(block_data.get("gasUsed", 0)),
            "transaction_count": len(block_data.get("transactions", [])),
            "size": int(block_data.get("size", 0)),
            "miner": block_data.get("miner", ""),  # Sequencer
        }
        
        # Base has very fast block times (~2 seconds)
        processed["block_time"] = 2.0
        processed["gas_utilization"] = processed["gas_used"] / processed["gas_limit"] if processed["gas_limit"] > 0 else 0
        
        # L2-specific fields
        processed["l2_block"] = True
        
        return processed
    
    async def process_transaction(self, tx_data: Dict[str, Any], block_data: Dict[str, Any]) -> ProcessedTransaction:
        """Process Base transaction with L2-specific considerations"""
        
        tx_type = "transfer"
        to_address = tx_data.get("to")
        input_data = tx_data.get("input", "0x")
        
        if not to_address:
            tx_type = "contract_creation"
        elif to_address.lower() in [addr.lower() for addr in self.l1_bridge_contracts.values()]:
            tx_type = "bridge_transaction"
        elif input_data and input_data != "0x":
            tx_type = "contract_call"
        
        gas_used = int(tx_data.get("gasUsed", 0))
        gas_price = int(tx_data.get("gasPrice", 0))
        
        return ProcessedTransaction(
            chain_id=self.chain_id,
            block_number=int(block_data.get("number", 0)),
            transaction_hash=tx_data.get("hash", ""),
            from_address=tx_data.get("from", ""),
            to_address=to_address,
            value=str(int(tx_data.get("value", 0))),
            gas_used=gas_used,
            gas_price=gas_price,
            transaction_fee=str(gas_used * gas_price),
            status="success" if tx_data.get("status") == "0x1" else "failed",
            transaction_type=tx_type,
            input_data_size=len(input_data) // 2 - 1 if input_data.startswith("0x") else len(input_data) // 2,
            timestamp=datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            extras={
                "nonce": int(tx_data.get("nonce", 0)),
                "transaction_index": int(tx_data.get("transactionIndex", 0)),
                "is_l2": True,
                "is_bridge_tx": tx_type == "bridge_transaction"
            }
        )
    
    async def process_events(self, tx_receipt: Optional[Dict[str, Any]], 
                           block_data: Dict[str, Any]) -> List[ProcessedEvent]:
        """Process Base events with L2 bridge detection"""
        return await super().process_events(tx_receipt, block_data)


class GLQProcessor(BaseChainProcessor):
    """GraphLinq Chain specialized processor"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient):
        super().__init__("glq", config, multichain_client)
        
        # GLQ-specific configurations
        self.supports_eip1559 = False  # Check actual GLQ implementation
        self.glq_specific_contracts = {
            # Add GLQ-specific contract addresses
        }
    
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GLQ block with chain-specific metrics"""
        
        processed = {
            "block_number": int(block_data.get("number", 0)),
            "timestamp": datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            "gas_limit": int(block_data.get("gasLimit", 0)),
            "gas_used": int(block_data.get("gasUsed", 0)),
            "transaction_count": len(block_data.get("transactions", [])),
            "size": int(block_data.get("size", 0)),
            "miner": block_data.get("miner", ""),
        }
        
        # GLQ-specific block time
        processed["block_time"] = 3.0  # Adjust based on actual GLQ block time
        processed["gas_utilization"] = processed["gas_used"] / processed["gas_limit"] if processed["gas_limit"] > 0 else 0
        
        return processed
    
    async def process_transaction(self, tx_data: Dict[str, Any], block_data: Dict[str, Any]) -> ProcessedTransaction:
        """Process GLQ transaction with chain-specific logic"""
        
        tx_type = "transfer"
        to_address = tx_data.get("to")
        input_data = tx_data.get("input", "0x")
        
        if not to_address:
            tx_type = "contract_creation"
        elif input_data and input_data != "0x":
            tx_type = "contract_call"
        
        gas_used = int(tx_data.get("gasUsed", 0))
        gas_price = int(tx_data.get("gasPrice", 0))
        
        return ProcessedTransaction(
            chain_id=self.chain_id,
            block_number=int(block_data.get("number", 0)),
            transaction_hash=tx_data.get("hash", ""),
            from_address=tx_data.get("from", ""),
            to_address=to_address,
            value=str(int(tx_data.get("value", 0))),
            gas_used=gas_used,
            gas_price=gas_price,
            transaction_fee=str(gas_used * gas_price),
            status="success" if tx_data.get("status") == "0x1" else "failed",
            transaction_type=tx_type,
            input_data_size=len(input_data) // 2 - 1 if input_data.startswith("0x") else len(input_data) // 2,
            timestamp=datetime.fromtimestamp(int(block_data.get("timestamp", 0)), timezone.utc),
            extras={
                "nonce": int(tx_data.get("nonce", 0)),
                "transaction_index": int(tx_data.get("transactionIndex", 0)),
                "is_glq_native": True
            }
        )
    
    async def process_events(self, tx_receipt: Optional[Dict[str, Any]], 
                           block_data: Dict[str, Any]) -> List[ProcessedEvent]:
        """Process GLQ events"""
        return await super().process_events(tx_receipt, block_data)


class ChainProcessorFactory:
    """Factory for creating chain-specific processors"""
    
    @staticmethod
    def create_processor(chain_id: str, config: Config, multichain_client: MultiChainClient) -> BaseChainProcessor:
        """Create appropriate processor for the given chain"""
        
        processor_map = {
            "ethereum": EthereumProcessor,
            "polygon": PolygonProcessor,
            "base": BaseProcessor,
            "avalanche": EthereumProcessor,  # Use Ethereum processor for Avalanche C-Chain (EVM compatible)
            "bsc": EthereumProcessor,       # Use Ethereum processor for BSC (EVM compatible)
            "glq": GLQProcessor
        }
        
        processor_class = processor_map.get(chain_id, BaseChainProcessor)
        
        if processor_class == BaseChainProcessor:
            logger.warning(f"No specific processor found for chain {chain_id}, using base processor")
        
        return processor_class(config, multichain_client)


# Enhanced Multi-Chain Processor using specialized processors
class EnhancedMultiChainProcessor:
    """Enhanced multi-chain processor using specialized chain processors"""
    
    def __init__(self, config: Config):
        self.config = config
        self.multichain_client: Optional[MultiChainClient] = None
        self.db_client: Optional[MultiChainInfluxDB] = None
        
        # Chain processors
        self.processors: Dict[str, BaseChainProcessor] = {}
        
    async def initialize(self):
        """Initialize the enhanced processor"""
        
        # Connect to clients
        self.multichain_client = MultiChainClient(self.config)
        await self.multichain_client.connect()
        
        self.db_client = MultiChainInfluxDB(self.config)
        await self.db_client.connect()
        
        # Create specialized processors for each connected chain
        for chain_id in self.multichain_client.get_connected_chains():
            processor = ChainProcessorFactory.create_processor(
                chain_id, self.config, self.multichain_client
            )
            self.processors[chain_id] = processor
            
        logger.info(f"Initialized enhanced processor with {len(self.processors)} chain processors")
    
    async def process_block_enhanced(self, chain_id: str, block_number: int) -> bool:
        """Process a single block using the chain-specific processor"""
        
        if chain_id not in self.processors:
            logger.error(f"No processor available for chain {chain_id}")
            return False
        
        try:
            processor = self.processors[chain_id]
            
            # Get block data
            block_data = await self.multichain_client.get_block(chain_id, block_number, True)
            if not block_data:
                logger.error(f"Failed to get block {block_number} from {chain_id}")
                return False
            
            # Process block
            processed_block = await processor.process_block(block_data)
            
            # Write block to database
            await self.db_client.write_block(chain_id, processed_block)
            
            # Process transactions
            for tx_data in block_data.get("transactions", []):
                if isinstance(tx_data, dict):  # Full transaction data
                    
                    # Get transaction receipt for events
                    tx_receipt = await self.multichain_client.get_transaction_receipt(
                        chain_id, tx_data["hash"]
                    )
                    
                    # Process transaction
                    processed_tx = await processor.process_transaction(tx_data, block_data)
                    await self.db_client.write_transaction(
                        chain_id, processed_tx.__dict__, processed_tx.block_number, processed_tx.status
                    )
                    
                    # Process events
                    events = await processor.process_events(tx_receipt, block_data)
                    for event in events:
                        await self.db_client.write_event(chain_id, event.__dict__)
                    
                    # Process token transfers
                    transfers = await processor.process_token_transfers(events)
                    for transfer in transfers:
                        await self.db_client.write_token_transfer(chain_id, transfer.__dict__)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing block {block_number} on {chain_id}: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the enhanced processor"""
        
        if self.multichain_client:
            await self.multichain_client.close()
        
        if self.db_client:
            await self.db_client.close()