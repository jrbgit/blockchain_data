"""
InfluxDB Client for Blockchain Analytics
Handles all database operations for storing and querying blockchain data.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json

from influxdb_client import InfluxDBClient as InfluxDB, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
import pandas as pd

logger = logging.getLogger(__name__)


class BlockchainInfluxDB:
    """InfluxDB client optimized for blockchain data storage."""
    
    def __init__(self, config_or_url = None, token: str = None, org: str = None, bucket: str = None):
        # Handle both Config objects and direct parameters
        if hasattr(config_or_url, 'get'):  # It's a Config object
            config = config_or_url
            self.url = config.get('influxdb.url', 'http://localhost:8086')
            self.token = config.influxdb_token
            self.org = config.get('influxdb.org', 'glq-analytics')
            self.bucket = config.get('influxdb.bucket', 'blockchain_data')
        else:  # Direct parameters
            self.url = config_or_url or 'http://localhost:8086'
            self.token = token or ''
            self.org = org or 'glq-analytics'
            self.bucket = bucket or 'blockchain_data'
        
        # Initialize client
        self.client = InfluxDB(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        
        # Connection state
        self._connected = False
        
    async def connect(self) -> bool:
        """Test connection to InfluxDB."""
        try:
            # Test with a simple ping
            health = self.client.health()
            if health.status == "pass":
                self._connected = True
                logger.info(f"Connected to InfluxDB at {self.url}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            
        return False
    
    def write_block(self, block_data: Dict[str, Any], block_time_diff: Optional[float] = None):
        """Write block data to InfluxDB."""
        try:
            # Convert timestamp
            timestamp = datetime.fromtimestamp(int(block_data['timestamp'], 16), tz=timezone.utc)
            
            # Calculate gas utilization
            gas_used = int(block_data['gasUsed'], 16)
            gas_limit = int(block_data['gasLimit'], 16)
            gas_utilization = gas_used / gas_limit if gas_limit > 0 else 0
            
            point = Point("blocks") \
                .tag("chain_id", "614") \
                .tag("network", "mainnet") \
                .tag("miner", block_data.get('miner', '0x0000000000000000000000000000000000000000')) \
                .field("block_number", int(block_data['number'], 16)) \
                .field("gas_limit", gas_limit) \
                .field("gas_used", gas_used) \
                .field("transaction_count", len(block_data.get('transactions', []))) \
                .field("size", int(block_data.get('size', '0x0'), 16)) \
                .field("difficulty", block_data.get('difficulty', '0x0')) \
                .field("total_difficulty", block_data.get('totalDifficulty', '0x0')) \
                .field("gas_utilization", gas_utilization) \
                .time(timestamp, WritePrecision.NS)
            
            # Add base fee if available (EIP-1559)
            if 'baseFeePerGas' in block_data:
                point = point.field("base_fee_per_gas", int(block_data['baseFeePerGas'], 16))
            
            # Add block time if calculated
            if block_time_diff:
                point = point.field("block_time", block_time_diff)
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            
        except Exception as e:
            logger.error(f"Error writing block data: {e}")
    
    def write_transaction(self, tx_data: Dict[str, Any], block_number: int, 
                         status: str = "success", gas_used: int = None):
        """Write transaction data to InfluxDB."""
        try:
            # Determine transaction type
            tx_type = self._classify_transaction(tx_data)
            
            # Calculate transaction fee
            gas_price = int(tx_data.get('gasPrice', '0x0'), 16)
            gas_limit = int(tx_data.get('gas', '0x0'), 16)
            actual_gas_used = gas_used or gas_limit
            transaction_fee = gas_price * actual_gas_used
            
            # Handle None values for to_address (contract creation)
            to_address = tx_data.get('to') 
            to_address_safe = to_address.lower() if to_address else ''
            
            point = Point("transactions") \
                .tag("chain_id", "614") \
                .tag("from_address", tx_data['from'].lower()) \
                .tag("to_address", to_address_safe) \
                .tag("transaction_type", tx_type) \
                .tag("status", status) \
                .field("block_number", block_number) \
                .field("transaction_index", int(tx_data['transactionIndex'], 16)) \
                .field("hash", tx_data['hash']) \
                .field("nonce", int(tx_data['nonce'], 16)) \
                .field("value", tx_data['value']) \
                .field("gas_limit", gas_limit) \
                .field("gas_used", actual_gas_used) \
                .field("gas_price", gas_price) \
                .field("transaction_fee", str(transaction_fee)) \
                .field("input_data_size", len(tx_data.get('input', '0x')) // 2) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            # Add effective gas price if available
            if 'effectiveGasPrice' in tx_data:
                point = point.field("effective_gas_price", int(tx_data['effectiveGasPrice'], 16))
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            
        except Exception as e:
            logger.error(f"Error writing transaction data: {e}")
    
    def write_event(self, event_data: Dict[str, Any], block_number: int, tx_hash: str):
        """Write event/log data to InfluxDB."""
        try:
            point = Point("events") \
                .tag("chain_id", "614") \
                .tag("contract_address", event_data['address'].lower()) \
                .tag("event_signature", event_data.get('topics', [''])[0]) \
                .field("block_number", block_number) \
                .field("transaction_hash", tx_hash) \
                .field("log_index", int(event_data.get('logIndex', '0x0'), 16)) \
                .field("data", event_data.get('data', '')) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            # Add topics as tags if available
            topics = event_data.get('topics', [])
            if len(topics) > 0:
                point = point.tag("topic0", topics[0])
            if len(topics) > 1:
                point = point.tag("topic1", topics[1])
            if len(topics) > 2:
                point = point.tag("topic2", topics[2])
            if len(topics) > 3:
                point = point.tag("topic3", topics[3])
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            
        except Exception as e:
            logger.error(f"Error writing event data: {e}")
    
    def write_token_transfer(self, transfer_data: Dict[str, Any]):
        """Write token transfer data."""
        try:
            point = Point("token_transfers") \
                .tag("chain_id", "614") \
                .tag("token_address", transfer_data['token_address'].lower()) \
                .tag("token_standard", transfer_data.get('standard', 'ERC20')) \
                .tag("from_address", transfer_data['from_address'].lower()) \
                .tag("to_address", transfer_data['to_address'].lower()) \
                .field("block_number", transfer_data['block_number']) \
                .field("transaction_hash", transfer_data['transaction_hash']) \
                .field("log_index", transfer_data.get('log_index', 0)) \
                .field("amount", transfer_data['amount']) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            # Add token metadata if available
            if 'token_name' in transfer_data:
                point = point.field("token_name", transfer_data['token_name'])
            if 'token_symbol' in transfer_data:
                point = point.field("token_symbol", transfer_data['token_symbol'])
            if 'token_decimals' in transfer_data:
                point = point.field("token_decimals", transfer_data['token_decimals'])
            if 'token_id' in transfer_data:  # For NFTs
                point = point.field("token_id", transfer_data['token_id'])
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            
        except Exception as e:
            logger.error(f"Error writing token transfer data: {e}")
    
    def write_contract(self, contract_data: Dict[str, Any]):
        """Write smart contract data."""
        try:
            point = Point("contracts") \
                .tag("chain_id", "614") \
                .tag("contract_address", contract_data['address'].lower()) \
                .tag("contract_type", contract_data.get('type', 'other')) \
                .tag("deployer_address", contract_data.get('deployer', '').lower()) \
                .field("deployment_block", contract_data.get('deployment_block', 0)) \
                .field("deployment_transaction", contract_data.get('deployment_tx', '')) \
                .field("bytecode_size", contract_data.get('bytecode_size', 0)) \
                .field("is_verified", contract_data.get('is_verified', False)) \
                .time(datetime.utcnow(), WritePrecision.NS)
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            
        except Exception as e:
            logger.error(f"Error writing contract data: {e}")
    
    def write_network_metrics(self, metrics_data: Dict[str, Any], period: str):
        """Write network-wide metrics."""
        try:
            point = Point("network_metrics") \
                .tag("chain_id", "614") \
                .tag("metric_type", period) \
                .tag("period", metrics_data.get('period_id', '')) \
                .field("start_block", metrics_data.get('start_block', 0)) \
                .field("end_block", metrics_data.get('end_block', 0)) \
                .field("avg_block_time", metrics_data.get('avg_block_time', 0.0)) \
                .field("total_transactions", metrics_data.get('total_transactions', 0)) \
                .field("total_gas_used", metrics_data.get('total_gas_used', 0)) \
                .field("avg_gas_price", metrics_data.get('avg_gas_price', 0.0)) \
                .field("active_addresses", metrics_data.get('active_addresses', 0)) \
                .field("new_contracts", metrics_data.get('new_contracts', 0)) \
                .field("total_value_transferred", metrics_data.get('total_value_transferred', '0')) \
                .time(datetime.utcnow(), WritePrecision.NS)
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            
        except Exception as e:
            logger.error(f"Error writing network metrics: {e}")
    
    def write_batch(self, points: List[Point]):
        """Write multiple points in batch for efficiency."""
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
        except Exception as e:
            logger.error(f"Error writing batch data: {e}")
    
    def query_latest_block(self) -> Optional[int]:
        """Get the latest block number stored in InfluxDB."""
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "blocks")
              |> filter(fn: (r) => r["_field"] == "block_number")
              |> last()
            '''
            
            result = self.query_api.query(org=self.org, query=query)
            
            for table in result:
                for record in table.records:
                    return int(record.get_value())
                    
        except Exception as e:
            logger.error(f"Error querying latest block: {e}")
            
        return None
    
    def query_block_range(self, start_block: int, end_block: int) -> pd.DataFrame:
        """Query block data for a specific range."""
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "blocks")
              |> filter(fn: (r) => r["block_number"] >= {start_block} and r["block_number"] <= {end_block})
            '''
            
            result = self.query_api.query_data_frame(org=self.org, query=query)
            return result
            
        except Exception as e:
            logger.error(f"Error querying block range: {e}")
            return pd.DataFrame()
    
    def query_address_activity(self, address: str, days: int = 7) -> pd.DataFrame:
        """Query transaction activity for a specific address."""
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r["_measurement"] == "transactions")
              |> filter(fn: (r) => r["from_address"] == "{address.lower()}" or r["to_address"] == "{address.lower()}")
            '''
            
            result = self.query_api.query_data_frame(org=self.org, query=query)
            return result
            
        except Exception as e:
            logger.error(f"Error querying address activity: {e}")
            return pd.DataFrame()
    
    def _classify_transaction(self, tx_data: Dict[str, Any]) -> str:
        """Classify transaction type based on data."""
        # Simple classification logic
        if not tx_data.get('to'):
            return "contract_creation"
        elif int(tx_data.get('value', '0x0'), 16) > 0:
            if len(tx_data.get('input', '0x')) > 2:
                return "contract_call"
            else:
                return "transfer"
        else:
            return "contract_call"
    
    def close(self):
        """Close InfluxDB connections."""
        if self.client:
            self.client.close()
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected


# Alias for compatibility
InfluxDBClient = BlockchainInfluxDB
