"""
Multi-Chain InfluxDB Client for Blockchain Analytics

This module extends the existing InfluxDB client to support multiple blockchain networks,
with chain-specific data storage and querying capabilities.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json

from influxdb_client import InfluxDBClient as InfluxDB, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
import pandas as pd

from .config import Config

logger = logging.getLogger(__name__)


class MultiChainInfluxDB:
    """Multi-chain InfluxDB client optimized for blockchain data storage across multiple networks."""
    
    def __init__(self, config: Config):
        self.config = config
        
        # InfluxDB connection parameters
        self.url = config.influxdb_url
        self.token = config.influxdb_token
        self.org = config.influxdb_org
        self.bucket = config.influxdb_bucket
        
        # Initialize client
        self.client = InfluxDB(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        
        # Chain configuration
        self.chains = config.chains
        
        # Connection state
        self._connected = False
        
        logger.info(f"Initialized multi-chain InfluxDB client for {len(self.chains)} chains")
    
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
    
    def get_chain_info(self, chain_id: str) -> Dict[str, Any]:
        """Get chain information for a given chain ID."""
        if chain_id not in self.chains:
            raise ValueError(f"Chain '{chain_id}' not configured")
        return self.chains[chain_id]
    
    def _get_chain_tags(self, chain_id: str) -> Dict[str, str]:
        """Get standard chain tags for data points."""
        chain_config = self.get_chain_info(chain_id)
        return {
            "chain_id": str(chain_config['chain_id']),
            "chain_name": chain_config['name'],
            "network": chain_config.get('network_type', 'mainnet'),
            "provider": chain_config.get('provider', 'unknown')
        }
    
    def write_block(self, chain_id: str, block_data: Dict[str, Any], block_time_diff: Optional[float] = None):
        """Write block data to InfluxDB with chain context."""
        try:
            # Convert timestamp
            timestamp = datetime.fromtimestamp(int(block_data['timestamp'], 16), tz=timezone.utc)
            
            # Calculate gas utilization
            gas_used = int(block_data['gasUsed'], 16)
            gas_limit = int(block_data['gasLimit'], 16)
            gas_utilization = gas_used / gas_limit if gas_limit > 0 else 0
            
            # Get chain tags
            chain_tags = self._get_chain_tags(chain_id)
            
            point = Point("blocks") \
                .tag("chain_id", chain_tags["chain_id"]) \
                .tag("chain_name", chain_tags["chain_name"]) \
                .tag("network", chain_tags["network"]) \
                .tag("provider", chain_tags["provider"]) \
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
            logger.error(f"Error writing block data for chain {chain_id}: {e}")
    
    def write_transaction(self, chain_id: str, tx_data: Dict[str, Any], block_number: int, 
                         status: str = "success", gas_used: int = None):
        """Write transaction data to InfluxDB with chain context."""
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
            
            # Get chain tags
            chain_tags = self._get_chain_tags(chain_id)
            
            point = Point("transactions") \
                .tag("chain_id", chain_tags["chain_id"]) \
                .tag("chain_name", chain_tags["chain_name"]) \
                .tag("network", chain_tags["network"]) \
                .tag("provider", chain_tags["provider"]) \
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
            logger.error(f"Error writing transaction data for chain {chain_id}: {e}")
    
    def write_event(self, chain_id: str, event_data: Dict[str, Any], block_number: int, tx_hash: str):
        """Write event/log data to InfluxDB with chain context."""
        try:
            # Get chain tags
            chain_tags = self._get_chain_tags(chain_id)
            
            point = Point("events") \
                .tag("chain_id", chain_tags["chain_id"]) \
                .tag("chain_name", chain_tags["chain_name"]) \
                .tag("network", chain_tags["network"]) \
                .tag("provider", chain_tags["provider"]) \
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
            logger.error(f"Error writing event data for chain {chain_id}: {e}")
    
    def write_token_transfer(self, chain_id: str, transfer_data: Dict[str, Any]):
        """Write token transfer data with chain context."""
        try:
            # Get chain tags
            chain_tags = self._get_chain_tags(chain_id)
            
            point = Point("token_transfers") \
                .tag("chain_id", chain_tags["chain_id"]) \
                .tag("chain_name", chain_tags["chain_name"]) \
                .tag("network", chain_tags["network"]) \
                .tag("provider", chain_tags["provider"]) \
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
            logger.error(f"Error writing token transfer data for chain {chain_id}: {e}")
    
    def write_contract(self, chain_id: str, contract_data: Dict[str, Any]):
        """Write smart contract data with chain context."""
        try:
            # Get chain tags
            chain_tags = self._get_chain_tags(chain_id)
            
            point = Point("contracts") \
                .tag("chain_id", chain_tags["chain_id"]) \
                .tag("chain_name", chain_tags["chain_name"]) \
                .tag("network", chain_tags["network"]) \
                .tag("provider", chain_tags["provider"]) \
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
            logger.error(f"Error writing contract data for chain {chain_id}: {e}")
    
    def write_network_metrics(self, chain_id: str, metrics_data: Dict[str, Any], period: str):
        """Write network-wide metrics with chain context."""
        try:
            # Get chain tags
            chain_tags = self._get_chain_tags(chain_id)
            
            point = Point("network_metrics") \
                .tag("chain_id", chain_tags["chain_id"]) \
                .tag("chain_name", chain_tags["chain_name"]) \
                .tag("network", chain_tags["network"]) \
                .tag("provider", chain_tags["provider"]) \
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
            logger.error(f"Error writing network metrics for chain {chain_id}: {e}")
    
    def write_cross_chain_metrics(self, metrics_data: Dict[str, Any]):
        """Write cross-chain comparison metrics."""
        try:
            point = Point("cross_chain_metrics") \
                .tag("metric_type", metrics_data.get('type', 'comparison')) \
                .field("chains_compared", json.dumps(metrics_data.get('chains', []))) \
                .field("total_chains", metrics_data.get('chain_count', 0)) \
                .field("total_blocks_processed", metrics_data.get('total_blocks', 0)) \
                .field("total_transactions", metrics_data.get('total_transactions', 0)) \
                .field("avg_block_time_across_chains", metrics_data.get('avg_block_time', 0.0)) \
                .field("chain_activity_scores", json.dumps(metrics_data.get('activity_scores', {}))) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            # Add individual chain metrics as separate fields
            for chain_id, chain_metrics in metrics_data.get('chain_specific', {}).items():
                point = point.field(f"chain_{chain_id}_latest_block", chain_metrics.get('latest_block', 0))
                point = point.field(f"chain_{chain_id}_tps", chain_metrics.get('tps', 0.0))
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            
        except Exception as e:
            logger.error(f"Error writing cross-chain metrics: {e}")
    
    def write_batch(self, points: List[Point]):
        """Write multiple points in batch for efficiency."""
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
        except Exception as e:
            logger.error(f"Error writing batch data: {e}")
    
    def query_latest_block(self, chain_id: Optional[str] = None) -> Optional[int]:
        """Get the latest block number stored in InfluxDB for a specific chain or all chains."""
        try:
            chain_filter = ""
            if chain_id:
                chain_config = self.get_chain_info(chain_id)
                chain_filter = f'|> filter(fn: (r) => r["chain_id"] == "{chain_config["chain_id"]}")'
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "blocks")
              |> filter(fn: (r) => r["_field"] == "block_number")
              {chain_filter}
              |> last()
            '''
            
            result = self.query_api.query(org=self.org, query=query)
            
            for table in result:
                for record in table.records:
                    return int(record.get_value())
                    
        except Exception as e:
            logger.error(f"Error querying latest block for chain {chain_id}: {e}")
            
        return None
    
    def query_latest_blocks_all_chains(self) -> Dict[str, Optional[int]]:
        """Get latest block numbers for all configured chains."""
        latest_blocks = {}
        
        for chain_id in self.chains.keys():
            try:
                latest_block = self.query_latest_block(chain_id)
                latest_blocks[chain_id] = latest_block
            except Exception as e:
                logger.error(f"Error getting latest block for {chain_id}: {e}")
                latest_blocks[chain_id] = None
        
        return latest_blocks
    
    def query_block_range(self, chain_id: str, start_block: int, end_block: int) -> pd.DataFrame:
        """Query block data for a specific range on a specific chain."""
        try:
            chain_config = self.get_chain_info(chain_id)
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "blocks")
              |> filter(fn: (r) => r["chain_id"] == "{chain_config['chain_id']}")
              |> filter(fn: (r) => r["block_number"] >= {start_block} and r["block_number"] <= {end_block})
            '''
            
            result = self.query_api.query_data_frame(org=self.org, query=query)
            return result
            
        except Exception as e:
            logger.error(f"Error querying block range for chain {chain_id}: {e}")
            return pd.DataFrame()
    
    def query_address_activity(self, address: str, chain_id: Optional[str] = None, days: int = 7) -> pd.DataFrame:
        """Query transaction activity for a specific address, optionally filtered by chain."""
        try:
            chain_filter = ""
            if chain_id:
                chain_config = self.get_chain_info(chain_id)
                chain_filter = f'|> filter(fn: (r) => r["chain_id"] == "{chain_config["chain_id"]}")'
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r["_measurement"] == "transactions")
              {chain_filter}
              |> filter(fn: (r) => r["from_address"] == "{address.lower()}" or r["to_address"] == "{address.lower()}")
            '''
            
            result = self.query_api.query_data_frame(org=self.org, query=query)
            return result
            
        except Exception as e:
            logger.error(f"Error querying address activity: {e}")
            return pd.DataFrame()
    
    def query_cross_chain_comparison(self, metric: str, timerange: str = "24h") -> pd.DataFrame:
        """Query cross-chain comparison data for a specific metric."""
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{timerange})
              |> filter(fn: (r) => r["_measurement"] == "network_metrics")
              |> filter(fn: (r) => r["_field"] == "{metric}")
              |> group(columns: ["chain_name"])
              |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
            '''
            
            result = self.query_api.query_data_frame(org=self.org, query=query)
            return result
            
        except Exception as e:
            logger.error(f"Error querying cross-chain comparison: {e}")
            return pd.DataFrame()
    
    def query_chain_activity_summary(self, timerange: str = "24h") -> Dict[str, Dict[str, Any]]:
        """Get activity summary for all chains."""
        summary = {}
        
        for chain_id, chain_config in self.chains.items():
            try:
                # Query basic metrics for each chain
                query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: -{timerange})
                  |> filter(fn: (r) => r["chain_id"] == "{chain_config['chain_id']}")
                  |> filter(fn: (r) => r["_measurement"] == "transactions")
                  |> count()
                '''
                
                result = self.query_api.query(org=self.org, query=query)
                tx_count = 0
                
                for table in result:
                    for record in table.records:
                        tx_count = record.get_value()
                        break
                
                summary[chain_id] = {
                    'chain_name': chain_config['name'],
                    'transaction_count': tx_count,
                    'provider': chain_config.get('provider', 'unknown')
                }
                
            except Exception as e:
                logger.error(f"Error getting activity summary for {chain_id}: {e}")
                summary[chain_id] = {
                    'chain_name': chain_config['name'],
                    'transaction_count': 0,
                    'error': str(e)
                }
        
        return summary
    
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
    
    async def delete_chain_data(self, chain_id: str, measurement: Optional[str] = None, 
                               start_time: str = "1970-01-01T00:00:00Z", end_time: str = None):
        """Delete data for a specific chain."""
        try:
            chain_config = self.get_chain_info(chain_id)
            
            if not end_time:
                end_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            
            delete_api = self.client.delete_api()
            
            # Build predicate for chain-specific deletion
            predicate = f'chain_id="{chain_config["chain_id"]}"'
            if measurement:
                predicate = f'_measurement="{measurement}" AND {predicate}'
            
            delete_api.delete(
                start=start_time,
                stop=end_time,
                predicate=predicate,
                bucket=self.bucket,
                org=self.org
            )
            
            logger.info(f"Deleted data for chain {chain_id} from measurement: {measurement or 'all'}")
            
        except Exception as e:
            logger.error(f"Error deleting data for chain {chain_id}: {e}")
            raise
    
    def close(self):
        """Close InfluxDB connections."""
        if self.client:
            self.client.close()
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected


# Backwards compatibility alias
MultiChainInfluxDBClient = MultiChainInfluxDB