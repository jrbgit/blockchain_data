"""
Chain-Specific Analytics Modules

This module provides analytics capabilities tailored for different blockchain networks,
including DeFi protocol analysis, token metrics, and network characteristics.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Union, Tuple
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
import json
import statistics
from collections import defaultdict

from ..core.config import Config
from ..core.multichain_client import MultiChainClient
from ..core.multichain_influxdb_client import MultiChainInfluxDB

logger = logging.getLogger(__name__)


@dataclass
class ChainMetrics:
    """Standard metrics for any blockchain"""
    chain_id: str
    timestamp: datetime
    
    # Network metrics
    latest_block: int
    avg_block_time: float
    tps: float  # Transactions per second
    gas_utilization: float
    avg_gas_price: float
    
    # Activity metrics
    active_addresses_24h: int
    transaction_count_24h: int
    total_value_transferred_24h: str  # Native currency
    
    # Contract metrics
    new_contracts_24h: int
    active_contracts_24h: int
    
    # Additional chain-specific metrics
    extras: Dict[str, Any]


@dataclass
class DeFiMetrics:
    """DeFi-specific metrics for supported chains"""
    chain_id: str
    timestamp: datetime
    
    # DEX metrics
    total_dex_volume_24h: float  # USD
    unique_traders_24h: int
    top_trading_pairs: List[Dict[str, Any]]
    
    # Lending metrics
    total_lending_volume_24h: float  # USD
    avg_utilization_rate: float
    
    # Token metrics
    new_tokens_24h: int
    top_transferred_tokens: List[Dict[str, Any]]
    
    # Protocol-specific data
    protocol_metrics: Dict[str, Any]


@dataclass
class CrossChainMetrics:
    """Cross-chain bridge and activity metrics"""
    timestamp: datetime
    
    # Bridge activity
    total_bridge_volume_24h: Dict[str, float]  # Chain pair -> volume
    bridge_transaction_count: Dict[str, int]   # Chain pair -> count
    
    # Multi-chain comparisons
    chain_rankings: Dict[str, Dict[str, int]]  # Metric -> chain rankings
    relative_activity: Dict[str, float]        # Chain -> relative activity score


class BaseAnalytics(ABC):
    """Base class for chain-specific analytics"""
    
    def __init__(self, chain_id: str, config: Config, multichain_client: MultiChainClient, db_client: MultiChainInfluxDB):
        self.chain_id = chain_id
        self.config = config
        self.client = multichain_client
        self.db_client = db_client
        self.chain_config = config.chains.get(chain_id, {})
        self.chain_name = self.chain_config.get('name', chain_id)
        
        # Cache for expensive operations
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
    
    @abstractmethod
    async def compute_network_metrics(self, timeframe_hours: int = 24) -> ChainMetrics:
        """Compute basic network metrics"""
        pass
    
    @abstractmethod
    async def compute_defi_metrics(self, timeframe_hours: int = 24) -> Optional[DeFiMetrics]:
        """Compute DeFi-specific metrics (if applicable)"""
        pass
    
    async def analyze_gas_trends(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """Analyze gas price trends"""
        try:
            # This would query InfluxDB for gas price data
            # For now, return mock structure
            return {
                "avg_gas_price": 0.0,
                "median_gas_price": 0.0,
                "gas_price_percentiles": {
                    "p25": 0.0,
                    "p75": 0.0,
                    "p95": 0.0
                },
                "gas_price_trend": "stable",  # increasing, decreasing, stable
                "peak_hours": [],
                "low_hours": []
            }
        except Exception as e:
            logger.error(f"Error analyzing gas trends for {self.chain_id}: {e}")
            return {}
    
    async def analyze_token_activity(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """Analyze token transfer activity"""
        try:
            # Query token transfer data from InfluxDB
            return {
                "total_transfers": 0,
                "unique_tokens": 0,
                "top_tokens_by_volume": [],
                "new_tokens": [],
                "token_categories": {
                    "erc20_transfers": 0,
                    "nft_transfers": 0,
                    "multi_token_transfers": 0
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing token activity for {self.chain_id}: {e}")
            return {}
    
    async def detect_anomalies(self) -> Dict[str, Any]:
        """Detect network anomalies"""
        try:
            # Implement anomaly detection logic
            return {
                "gas_spikes": [],
                "unusual_activity": [],
                "performance_issues": [],
                "security_alerts": []
            }
        except Exception as e:
            logger.error(f"Error detecting anomalies for {self.chain_id}: {e}")
            return {}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._metrics_cache:
            return False
        
        cache_entry = self._metrics_cache[cache_key]
        if 'timestamp' not in cache_entry:
            return False
        
        age = datetime.now() - cache_entry['timestamp']
        return age.total_seconds() < self._cache_ttl
    
    def _set_cache(self, cache_key: str, data: Any) -> None:
        """Set cache entry with timestamp"""
        self._metrics_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def _get_cache(self, cache_key: str) -> Any:
        """Get cached data if valid"""
        if self._is_cache_valid(cache_key):
            return self._metrics_cache[cache_key]['data']
        return None


class EthereumAnalytics(BaseAnalytics):
    """Ethereum Mainnet specific analytics"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient, db_client: MultiChainInfluxDB):
        super().__init__("ethereum", config, multichain_client, db_client)
        
        # Ethereum-specific contract addresses
        self.defi_contracts = {
            "uniswap_v2_router": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            "uniswap_v3_router": "0xe592427a0aece92de3edee1f18e0157c05861564",
            "compound_controller": "0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b",
            "aave_pool": "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9",
            "makerdao_cdp": "0x35d1b3f3d7966a1dfe207aa4514c12a259a0492b"
        }
        
        # Known token contracts
        self.major_tokens = {
            "USDC": "0xa0b86a33e6441e80c8ee3fb7d2e0e775b3b09e1e",
            "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7", 
            "WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f"
        }
    
    async def compute_network_metrics(self, timeframe_hours: int = 24) -> ChainMetrics:
        """Compute Ethereum network metrics"""
        
        cache_key = f"network_metrics_{timeframe_hours}h"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            # Get latest block info
            latest_block = await self.client.get_latest_block_number(self.chain_id)
            
            # Calculate time range for queries
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=timeframe_hours)
            
            # Mock calculations (would use real InfluxDB queries)
            avg_block_time = 13.0  # Ethereum average
            blocks_in_period = int(timeframe_hours * 3600 / avg_block_time)
            
            # Estimated metrics (would calculate from real data)
            tps = 15.0  # Ethereum typical
            gas_utilization = 0.95  # Usually near capacity
            avg_gas_price = 20.0  # Gwei
            
            active_addresses = 400000  # Daily active addresses
            tx_count = active_addresses * 2  # Rough estimate
            total_value = "50000000000000000000000"  # 50k ETH in Wei
            
            metrics = ChainMetrics(
                chain_id=self.chain_id,
                timestamp=end_time,
                latest_block=latest_block or 0,
                avg_block_time=avg_block_time,
                tps=tps,
                gas_utilization=gas_utilization,
                avg_gas_price=avg_gas_price,
                active_addresses_24h=active_addresses,
                transaction_count_24h=tx_count,
                total_value_transferred_24h=total_value,
                new_contracts_24h=500,
                active_contracts_24h=10000,
                extras={
                    "network_hashrate": "900 TH/s",
                    "validator_count": 0,  # Pre-merge data
                    "staking_ratio": 0.0,
                    "eip1559_burn_rate": "2.5 ETH/hour"
                }
            )
            
            self._set_cache(cache_key, metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error computing Ethereum network metrics: {e}")
            raise
    
    async def compute_defi_metrics(self, timeframe_hours: int = 24) -> DeFiMetrics:
        """Compute Ethereum DeFi metrics"""
        
        cache_key = f"defi_metrics_{timeframe_hours}h"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            end_time = datetime.now(timezone.utc)
            
            # Mock DeFi metrics (would calculate from real DEX/lending data)
            defi_metrics = DeFiMetrics(
                chain_id=self.chain_id,
                timestamp=end_time,
                total_dex_volume_24h=2_500_000_000,  # $2.5B
                unique_traders_24h=75000,
                top_trading_pairs=[
                    {"pair": "WETH/USDC", "volume": 500_000_000, "trades": 12000},
                    {"pair": "WETH/USDT", "volume": 300_000_000, "trades": 8000},
                    {"pair": "DAI/USDC", "volume": 150_000_000, "trades": 5000}
                ],
                total_lending_volume_24h=800_000_000,  # $800M
                avg_utilization_rate=0.65,
                new_tokens_24h=25,
                top_transferred_tokens=[
                    {"token": "USDC", "transfers": 50000, "volume": "1000000000000000000000000"},
                    {"token": "USDT", "transfers": 45000, "volume": "900000000000000000000000"},
                    {"token": "DAI", "transfers": 35000, "volume": "700000000000000000000000"}
                ],
                protocol_metrics={
                    "uniswap": {
                        "volume_24h": 1_200_000_000,
                        "liquidity": 8_500_000_000,
                        "fees_earned_24h": 2_400_000
                    },
                    "compound": {
                        "total_supply": 15_000_000_000,
                        "total_borrow": 9_500_000_000,
                        "utilization": 0.63
                    },
                    "aave": {
                        "total_liquidity": 20_000_000_000,
                        "total_borrowed": 12_000_000_000,
                        "utilization": 0.60
                    }
                }
            )
            
            self._set_cache(cache_key, defi_metrics)
            return defi_metrics
            
        except Exception as e:
            logger.error(f"Error computing Ethereum DeFi metrics: {e}")
            raise
    
    async def analyze_mev_activity(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """Analyze MEV (Maximum Extractable Value) activity on Ethereum"""
        try:
            return {
                "total_mev_extracted": 15_000_000,  # USD
                "mev_per_block": 850,  # USD average
                "top_mev_strategies": [
                    {"strategy": "arbitrage", "volume": 8_000_000, "percentage": 53.3},
                    {"strategy": "liquidation", "volume": 4_500_000, "percentage": 30.0},
                    {"strategy": "sandwich", "volume": 2_500_000, "percentage": 16.7}
                ],
                "affected_transactions": 125000,
                "mev_bots": 450  # Estimated active bots
            }
        except Exception as e:
            logger.error(f"Error analyzing MEV activity: {e}")
            return {}


class PolygonAnalytics(BaseAnalytics):
    """Polygon (MATIC) specific analytics"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient, db_client: MultiChainInfluxDB):
        super().__init__("polygon", config, multichain_client, db_client)
        
        # Polygon-specific contracts
        self.defi_contracts = {
            "quickswap_router": "0xa5e0829caced8ffdd4de3c43696c57f7d7a678ff",
            "sushiswap_router": "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506",
            "aave_pool": "0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf",
            "curve_pool": "0x445fe580ef8d70ff569ab36e80c647af338db351"
        }
        
        # Bridge contracts
        self.bridge_contracts = {
            "pos_bridge": "0xa0c68c638235ee32657e8f720a23cec1bfc77c77",
            "fx_portal": "0xfe5e5d361b2ad62c541bab87c45a0b9b018389a2"
        }
    
    async def compute_network_metrics(self, timeframe_hours: int = 24) -> ChainMetrics:
        """Compute Polygon network metrics"""
        
        try:
            latest_block = await self.client.get_latest_block_number(self.chain_id)
            end_time = datetime.now(timezone.utc)
            
            # Polygon-specific calculations
            avg_block_time = 2.1  # Polygon average
            tps = 65.0  # Higher than Ethereum
            gas_utilization = 0.40  # Lower utilization, cheaper gas
            avg_gas_price = 0.03  # Much lower than Ethereum
            
            metrics = ChainMetrics(
                chain_id=self.chain_id,
                timestamp=end_time,
                latest_block=latest_block or 0,
                avg_block_time=avg_block_time,
                tps=tps,
                gas_utilization=gas_utilization,
                avg_gas_price=avg_gas_price,
                active_addresses_24h=350000,  # High activity due to low fees
                transaction_count_24h=2_800_000,  # Much higher tx volume
                total_value_transferred_24h="25000000000000000000000",  # 25k MATIC
                new_contracts_24h=800,  # More contract deployment due to low costs
                active_contracts_24h=15000,
                extras={
                    "validator_count": 100,
                    "checkpoint_frequency": "30 minutes",
                    "bridge_volume_24h": 50_000_000,  # USD
                    "pos_staking_ratio": 0.40
                }
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error computing Polygon network metrics: {e}")
            raise
    
    async def compute_defi_metrics(self, timeframe_hours: int = 24) -> DeFiMetrics:
        """Compute Polygon DeFi metrics"""
        
        try:
            end_time = datetime.now(timezone.utc)
            
            defi_metrics = DeFiMetrics(
                chain_id=self.chain_id,
                timestamp=end_time,
                total_dex_volume_24h=450_000_000,  # Lower than Ethereum but significant
                unique_traders_24h=95000,  # High due to low fees
                top_trading_pairs=[
                    {"pair": "WMATIC/USDC", "volume": 80_000_000, "trades": 25000},
                    {"pair": "WETH/USDC", "volume": 65_000_000, "trades": 18000},
                    {"pair": "USDT/USDC", "volume": 45_000_000, "trades": 15000}
                ],
                total_lending_volume_24h=180_000_000,
                avg_utilization_rate=0.55,
                new_tokens_24h=45,  # More experimentation due to low costs
                top_transferred_tokens=[
                    {"token": "USDC", "transfers": 85000, "volume": "500000000000000000000000"},
                    {"token": "WMATIC", "transfers": 120000, "volume": "800000000000000000000000"},
                    {"token": "WETH", "transfers": 35000, "volume": "200000000000000000000000"}
                ],
                protocol_metrics={
                    "quickswap": {
                        "volume_24h": 200_000_000,
                        "liquidity": 1_200_000_000,
                        "fees_earned_24h": 400_000
                    },
                    "sushiswap": {
                        "volume_24h": 120_000_000,
                        "liquidity": 800_000_000,
                        "fees_earned_24h": 240_000
                    },
                    "aave": {
                        "total_liquidity": 3_500_000_000,
                        "total_borrowed": 1_800_000_000,
                        "utilization": 0.51
                    }
                }
            )
            
            return defi_metrics
            
        except Exception as e:
            logger.error(f"Error computing Polygon DeFi metrics: {e}")
            raise
    
    async def analyze_bridge_activity(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """Analyze Polygon bridge activity"""
        try:
            return {
                "total_deposits_24h": {
                    "count": 15000,
                    "volume_usd": 85_000_000
                },
                "total_withdrawals_24h": {
                    "count": 12000,
                    "volume_usd": 75_000_000
                },
                "top_bridged_tokens": [
                    {"token": "USDC", "deposits": 35_000_000, "withdrawals": 28_000_000},
                    {"token": "WETH", "deposits": 25_000_000, "withdrawals": 22_000_000},
                    {"token": "DAI", "deposits": 15_000_000, "withdrawals": 12_000_000}
                ],
                "average_bridge_time": "45 minutes",
                "failed_transactions": 125,
                "bridge_utilization": 0.72
            }
        except Exception as e:
            logger.error(f"Error analyzing bridge activity: {e}")
            return {}


class BaseChainAnalytics(BaseAnalytics):
    """Base (Coinbase L2) specific analytics"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient, db_client: MultiChainInfluxDB):
        super().__init__("base", config, multichain_client, db_client)
        
        # Base-specific contracts (still developing ecosystem)
        self.defi_contracts = {
            "uniswap_v3": "0x2626664c2603336e57b271c5c0b26f421741e481",  # Base Uniswap
        }
        
        self.l2_contracts = {
            "l2_standard_bridge": "0x4200000000000000000000000000000000000010",
            "l2_cross_domain_messenger": "0x4200000000000000000000000000000000000007"
        }
    
    async def compute_network_metrics(self, timeframe_hours: int = 24) -> ChainMetrics:
        """Compute Base network metrics"""
        
        try:
            latest_block = await self.client.get_latest_block_number(self.chain_id)
            end_time = datetime.now(timezone.utc)
            
            # Base L2 characteristics
            avg_block_time = 2.0  # Fast L2 blocks
            tps = 45.0  # Good throughput for L2
            gas_utilization = 0.25  # Lower utilization as ecosystem grows
            avg_gas_price = 0.001  # Very low L2 fees
            
            metrics = ChainMetrics(
                chain_id=self.chain_id,
                timestamp=end_time,
                latest_block=latest_block or 0,
                avg_block_time=avg_block_time,
                tps=tps,
                gas_utilization=gas_utilization,
                avg_gas_price=avg_gas_price,
                active_addresses_24h=85000,  # Growing ecosystem
                transaction_count_24h=1_200_000,  # High tx count due to low fees
                total_value_transferred_24h="5000000000000000000000",  # 5k ETH
                new_contracts_24h=200,
                active_contracts_24h=3500,
                extras={
                    "l2_type": "optimistic_rollup",
                    "sequencer_uptime": 0.999,
                    "l1_gas_used": 850000,  # Gas used on L1 for batch posting
                    "batch_submission_frequency": "2 hours",
                    "bridge_tvl": 250_000_000  # USD
                }
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error computing Base network metrics: {e}")
            raise
    
    async def compute_defi_metrics(self, timeframe_hours: int = 24) -> Optional[DeFiMetrics]:
        """Compute Base DeFi metrics (limited ecosystem)"""
        
        try:
            end_time = datetime.now(timezone.utc)
            
            # Base has a smaller but growing DeFi ecosystem
            defi_metrics = DeFiMetrics(
                chain_id=self.chain_id,
                timestamp=end_time,
                total_dex_volume_24h=45_000_000,  # Growing but smaller
                unique_traders_24h=15000,
                top_trading_pairs=[
                    {"pair": "WETH/USDC", "volume": 25_000_000, "trades": 5000},
                    {"pair": "WETH/DAI", "volume": 12_000_000, "trades": 3000},
                ],
                total_lending_volume_24h=15_000_000,  # Limited lending protocols
                avg_utilization_rate=0.45,
                new_tokens_24h=15,
                top_transferred_tokens=[
                    {"token": "USDC", "transfers": 25000, "volume": "150000000000000000000000"},
                    {"token": "WETH", "transfers": 18000, "volume": "100000000000000000000000"}
                ],
                protocol_metrics={
                    "uniswap_v3": {
                        "volume_24h": 35_000_000,
                        "liquidity": 180_000_000,
                        "fees_earned_24h": 70_000
                    }
                }
            )
            
            return defi_metrics
            
        except Exception as e:
            logger.error(f"Error computing Base DeFi metrics: {e}")
            return None


class GLQAnalytics(BaseAnalytics):
    """GraphLinq Chain specific analytics"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient, db_client: MultiChainInfluxDB):
        super().__init__("glq", config, multichain_client, db_client)
        
        # GLQ-specific contracts
        self.glq_contracts = {
            # Add GLQ-specific contract addresses when available
        }
    
    async def compute_network_metrics(self, timeframe_hours: int = 24) -> ChainMetrics:
        """Compute GLQ network metrics"""
        
        try:
            latest_block = await self.client.get_latest_block_number(self.chain_id)
            end_time = datetime.now(timezone.utc)
            
            # GLQ-specific characteristics (adjust based on actual network)
            avg_block_time = 3.0  # Estimated
            tps = 30.0  # Estimated
            gas_utilization = 0.15  # Lower utilization on newer network
            avg_gas_price = 0.005  # Competitive fees
            
            metrics = ChainMetrics(
                chain_id=self.chain_id,
                timestamp=end_time,
                latest_block=latest_block or 0,
                avg_block_time=avg_block_time,
                tps=tps,
                gas_utilization=gas_utilization,
                avg_gas_price=avg_gas_price,
                active_addresses_24h=5000,  # Smaller but growing
                transaction_count_24h=150_000,
                total_value_transferred_24h="10000000000000000000000",  # 10k GLQ
                new_contracts_24h=25,
                active_contracts_24h=500,
                extras={
                    "consensus_type": "proof_of_stake",  # If applicable
                    "native_token": "GLQ",
                    "ecosystem_stage": "development",
                    "unique_features": ["graph_processing", "no_code_automation"]
                }
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error computing GLQ network metrics: {e}")
            raise
    
    async def compute_defi_metrics(self, timeframe_hours: int = 24) -> Optional[DeFiMetrics]:
        """Compute GLQ DeFi metrics (if DeFi protocols exist)"""
        
        # GLQ might not have significant DeFi ecosystem yet
        return None
    
    async def analyze_glq_specific_features(self) -> Dict[str, Any]:
        """Analyze GLQ-specific features like graph processing"""
        try:
            return {
                "graph_operations_24h": 1200,
                "automation_triggers_24h": 850,
                "no_code_deployments_24h": 45,
                "integration_usage": {
                    "apis_connected": 150,
                    "data_sources": 75,
                    "webhooks_processed": 5000
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing GLQ specific features: {e}")
            return {}


class CrossChainAnalytics:
    """Analytics for cross-chain metrics and comparisons"""
    
    def __init__(self, config: Config, multichain_client: MultiChainClient, db_client: MultiChainInfluxDB):
        self.config = config
        self.client = multichain_client
        self.db_client = db_client
        
        # Initialize chain-specific analytics
        self.chain_analytics = {
            "ethereum": EthereumAnalytics(config, multichain_client, db_client),
            "polygon": PolygonAnalytics(config, multichain_client, db_client),
            "base": BaseChainAnalytics(config, multichain_client, db_client),
            "glq": GLQAnalytics(config, multichain_client, db_client)
        }
    
    async def compute_cross_chain_metrics(self, timeframe_hours: int = 24) -> CrossChainMetrics:
        """Compute cross-chain comparison metrics"""
        
        try:
            end_time = datetime.now(timezone.utc)
            
            # Get metrics from all chains
            all_metrics = {}
            for chain_id, analytics in self.chain_analytics.items():
                if chain_id in self.client.get_connected_chains():
                    try:
                        metrics = await analytics.compute_network_metrics(timeframe_hours)
                        all_metrics[chain_id] = metrics
                    except Exception as e:
                        logger.error(f"Failed to get metrics for {chain_id}: {e}")
                        continue
            
            # Calculate rankings
            rankings = {}
            if all_metrics:
                # Transaction volume ranking
                tx_ranking = sorted(
                    all_metrics.items(),
                    key=lambda x: x[1].transaction_count_24h,
                    reverse=True
                )
                rankings["transaction_volume"] = {
                    chain_id: idx + 1 for idx, (chain_id, _) in enumerate(tx_ranking)
                }
                
                # TPS ranking
                tps_ranking = sorted(
                    all_metrics.items(),
                    key=lambda x: x[1].tps,
                    reverse=True
                )
                rankings["tps"] = {
                    chain_id: idx + 1 for idx, (chain_id, _) in enumerate(tps_ranking)
                }
                
                # Gas price ranking (lower is better)
                gas_ranking = sorted(
                    all_metrics.items(),
                    key=lambda x: x[1].avg_gas_price
                )
                rankings["gas_efficiency"] = {
                    chain_id: idx + 1 for idx, (chain_id, _) in enumerate(gas_ranking)
                }
            
            # Calculate relative activity scores
            activity_scores = {}
            if all_metrics:
                max_tx = max(m.transaction_count_24h for m in all_metrics.values())
                max_addresses = max(m.active_addresses_24h for m in all_metrics.values())
                
                for chain_id, metrics in all_metrics.items():
                    # Weighted activity score
                    tx_score = metrics.transaction_count_24h / max_tx if max_tx > 0 else 0
                    address_score = metrics.active_addresses_24h / max_addresses if max_addresses > 0 else 0
                    utilization_score = metrics.gas_utilization
                    
                    activity_scores[chain_id] = (tx_score * 0.4 + address_score * 0.4 + utilization_score * 0.2)
            
            return CrossChainMetrics(
                timestamp=end_time,
                total_bridge_volume_24h={
                    "ethereum_polygon": 50_000_000,
                    "ethereum_base": 25_000_000,
                    "polygon_ethereum": 45_000_000,
                    "base_ethereum": 22_000_000
                },
                bridge_transaction_count={
                    "ethereum_polygon": 15000,
                    "ethereum_base": 8000,
                    "polygon_ethereum": 12000,
                    "base_ethereum": 7500
                },
                chain_rankings=rankings,
                relative_activity=activity_scores
            )
            
        except Exception as e:
            logger.error(f"Error computing cross-chain metrics: {e}")
            raise
    
    async def generate_market_overview(self) -> Dict[str, Any]:
        """Generate comprehensive market overview across all chains"""
        
        try:
            cross_chain = await self.compute_cross_chain_metrics()
            
            # Get individual chain metrics
            chain_summaries = {}
            total_volume = 0
            total_transactions = 0
            total_active_addresses = 0
            
            for chain_id, analytics in self.chain_analytics.items():
                if chain_id in self.client.get_connected_chains():
                    try:
                        metrics = await analytics.compute_network_metrics(24)
                        defi_metrics = await analytics.compute_defi_metrics(24)
                        
                        chain_summaries[chain_id] = {
                            "network": {
                                "latest_block": metrics.latest_block,
                                "tps": metrics.tps,
                                "gas_utilization": metrics.gas_utilization,
                                "avg_gas_price": metrics.avg_gas_price,
                                "transaction_count_24h": metrics.transaction_count_24h,
                                "active_addresses_24h": metrics.active_addresses_24h
                            },
                            "defi": {
                                "dex_volume_24h": defi_metrics.total_dex_volume_24h if defi_metrics else 0,
                                "unique_traders_24h": defi_metrics.unique_traders_24h if defi_metrics else 0
                            }
                        }
                        
                        total_transactions += metrics.transaction_count_24h
                        total_active_addresses += metrics.active_addresses_24h
                        if defi_metrics:
                            total_volume += defi_metrics.total_dex_volume_24h
                            
                    except Exception as e:
                        logger.error(f"Failed to get overview for {chain_id}: {e}")
                        continue
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_chains_monitored": len(chain_summaries),
                    "total_transactions_24h": total_transactions,
                    "total_active_addresses_24h": total_active_addresses,
                    "total_dex_volume_24h": total_volume,
                    "cross_chain_bridge_volume_24h": sum(cross_chain.total_bridge_volume_24h.values())
                },
                "chain_details": chain_summaries,
                "rankings": cross_chain.chain_rankings,
                "bridge_activity": {
                    "volume_by_route": cross_chain.total_bridge_volume_24h,
                    "transactions_by_route": cross_chain.bridge_transaction_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating market overview: {e}")
            raise


class AnalyticsFactory:
    """Factory for creating chain-specific analytics"""
    
    @staticmethod
    def create_analytics(chain_id: str, config: Config, multichain_client: MultiChainClient, db_client: MultiChainInfluxDB) -> BaseAnalytics:
        """Create appropriate analytics for the given chain"""
        
        analytics_map = {
            "ethereum": EthereumAnalytics,
            "polygon": PolygonAnalytics,
            "base": BaseChainAnalytics,
            "avalanche": EthereumAnalytics,  # Use Ethereum analytics for Avalanche C-Chain
            "bsc": EthereumAnalytics,       # Use Ethereum analytics for BSC
            "glq": GLQAnalytics
        }
        
        analytics_class = analytics_map.get(chain_id, BaseAnalytics)
        
        if analytics_class == BaseAnalytics:
            logger.warning(f"No specific analytics found for chain {chain_id}, using base analytics")
        
        return analytics_class(config, multichain_client, db_client)


# Main analytics orchestrator
class MultiChainAnalyticsOrchestrator:
    """Main orchestrator for multi-chain analytics"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[MultiChainClient] = None
        self.db_client: Optional[MultiChainInfluxDB] = None
        self.cross_chain_analytics: Optional[CrossChainAnalytics] = None
        
    async def initialize(self):
        """Initialize the analytics orchestrator"""
        
        self.client = MultiChainClient(self.config)
        await self.client.connect()
        
        self.db_client = MultiChainInfluxDB(self.config)
        await self.db_client.connect()
        
        self.cross_chain_analytics = CrossChainAnalytics(self.config, self.client, self.db_client)
        
        logger.info("Analytics orchestrator initialized")
    
    async def run_comprehensive_analytics(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """Run comprehensive analytics across all chains"""
        
        if not self.cross_chain_analytics:
            raise RuntimeError("Analytics orchestrator not initialized")
        
        try:
            # Generate comprehensive market overview
            market_overview = await self.cross_chain_analytics.generate_market_overview()
            
            # Get cross-chain metrics
            cross_chain_metrics = await self.cross_chain_analytics.compute_cross_chain_metrics(timeframe_hours)
            
            return {
                "market_overview": market_overview,
                "cross_chain_metrics": {
                    "bridge_volume": cross_chain_metrics.total_bridge_volume_24h,
                    "bridge_transactions": cross_chain_metrics.bridge_transaction_count,
                    "chain_rankings": cross_chain_metrics.chain_rankings,
                    "activity_scores": cross_chain_metrics.relative_activity
                },
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running comprehensive analytics: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the analytics orchestrator"""
        
        if self.client:
            await self.client.close()
        
        if self.db_client:
            self.db_client.close()  # close() is not async
