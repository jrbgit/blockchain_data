"""
Blockchain RPC Client for GraphLinq Chain
Handles all blockchain interactions with robust error handling and connection pooling.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import time

import aiohttp
from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    # For newer versions of web3.py
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BlockchainClient:
    """High-performance blockchain client with connection pooling and error handling."""
    
    def __init__(self, rpc_url: str = "http://localhost:8545", 
                 ws_url: Optional[str] = None,
                 max_connections: int = 20,
                 timeout: int = 30):
        self.rpc_url = rpc_url
        self.ws_url = ws_url
        self.max_connections = max_connections
        self.timeout = timeout
        
        # Initialize Web3 instance
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Add POA middleware for chains that might need it
        try:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except Exception:
            # For newer web3.py versions, try different approach
            pass
        
        # Initialize HTTP session with connection pooling
        self.session = self._create_session()
        
        # Connection state
        self._connected = False
        self._chain_id = None
        self._latest_block = None
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.01  # 100 requests/second max
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with connection pooling and retry strategy."""
        session = requests.Session()
        
        # Retry strategy
        try:
            # For older urllib3 versions
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "POST"],
                backoff_factor=1
            )
        except TypeError:
            # For newer urllib3 versions
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "POST"],
                backoff_factor=1
            )
        
        adapter = HTTPAdapter(
            pool_connections=self.max_connections,
            pool_maxsize=self.max_connections,
            max_retries=retry_strategy
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
        
    async def connect(self) -> bool:
        """Test connection and get basic chain info."""
        try:
            # Test basic connectivity
            chain_id = await self.get_chain_id()
            latest_block = await self.get_latest_block_number()
            
            if chain_id and latest_block:
                self._connected = True
                self._chain_id = chain_id
                self._latest_block = latest_block
                
                logger.info(f"Connected to blockchain - Chain ID: {chain_id}, Latest block: {latest_block}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to blockchain: {e}")
            
        return False
        
    def _rate_limit(self):
        """Simple rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
            
        self._last_request_time = time.time()
        
    async def _make_rpc_call(self, method: str, params: List = None) -> Dict[str, Any]:
        """Make async RPC call with error handling."""
        if params is None:
            params = []
            
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        self._rate_limit()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if "error" in result:
                            logger.error(f"RPC error for {method}: {result['error']}")
                            return None
                            
                        return result.get("result")
                    else:
                        logger.error(f"HTTP error {response.status} for {method}")
                        return None
                        
        except Exception as e:
            logger.error(f"Exception in RPC call {method}: {e}")
            return None
            
    def _make_sync_rpc_call(self, method: str, params: List = None) -> Dict[str, Any]:
        """Make synchronous RPC call."""
        if params is None:
            params = []
            
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        self._rate_limit()
        
        try:
            response = self.session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if "error" in result:
                    logger.error(f"RPC error for {method}: {result['error']}")
                    return None
                    
                return result.get("result")
            else:
                logger.error(f"HTTP error {response.status_code} for {method}")
                return None
                
        except Exception as e:
            logger.error(f"Exception in sync RPC call {method}: {e}")
            return None
    
    # Blockchain query methods
    async def get_chain_id(self) -> Optional[int]:
        """Get chain ID."""
        result = await self._make_rpc_call("eth_chainId")
        return int(result, 16) if result else None
        
    async def get_latest_block_number(self) -> Optional[int]:
        """Get latest block number."""
        result = await self._make_rpc_call("eth_blockNumber")
        return int(result, 16) if result else None
        
    async def get_block(self, block_number: Union[int, str], 
                       include_transactions: bool = True) -> Optional[Dict[str, Any]]:
        """Get block by number or hash."""
        if isinstance(block_number, int):
            block_identifier = hex(block_number)
        else:
            block_identifier = block_number
            
        result = await self._make_rpc_call("eth_getBlockByNumber", 
                                          [block_identifier, include_transactions])
        return result
        
    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction by hash."""
        return await self._make_rpc_call("eth_getTransactionByHash", [tx_hash])
        
    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt."""
        return await self._make_rpc_call("eth_getTransactionReceipt", [tx_hash])
        
    async def get_logs(self, from_block: int, to_block: int, 
                      addresses: List[str] = None, 
                      topics: List[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get logs/events for block range."""
        filter_params = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block)
        }
        
        if addresses:
            filter_params["address"] = addresses
        if topics:
            filter_params["topics"] = topics
            
        return await self._make_rpc_call("eth_getLogs", [filter_params])
        
    async def get_code(self, address: str, block_number: Union[int, str] = "latest") -> Optional[str]:
        """Get contract code at address."""
        if isinstance(block_number, int):
            block_identifier = hex(block_number)
        else:
            block_identifier = block_number
            
        return await self._make_rpc_call("eth_getCode", [address, block_identifier])
        
    async def get_balance(self, address: str, block_number: Union[int, str] = "latest") -> Optional[int]:
        """Get ETH balance for address."""
        if isinstance(block_number, int):
            block_identifier = hex(block_number)
        else:
            block_identifier = block_number
            
        result = await self._make_rpc_call("eth_getBalance", [address, block_identifier])
        return int(result, 16) if result else None
        
    async def get_transaction_count(self, address: str, 
                                   block_number: Union[int, str] = "latest") -> Optional[int]:
        """Get transaction count (nonce) for address."""
        if isinstance(block_number, int):
            block_identifier = hex(block_number)
        else:
            block_identifier = block_number
            
        result = await self._make_rpc_call("eth_getTransactionCount", [address, block_identifier])
        return int(result, 16) if result else None
        
    # Batch operations for efficiency
    async def get_blocks_batch(self, start_block: int, end_block: int) -> List[Optional[Dict[str, Any]]]:
        """Get multiple blocks in batch."""
        tasks = []
        
        for block_num in range(start_block, end_block + 1):
            tasks.append(self.get_block(block_num, include_transactions=True))
            
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    def get_block_sync(self, block_number: Union[int, str], 
                      include_transactions: bool = True) -> Optional[Dict[str, Any]]:
        """Synchronous version of get_block for use in non-async contexts."""
        if isinstance(block_number, int):
            block_identifier = hex(block_number)
        else:
            block_identifier = block_number
            
        return self._make_sync_rpc_call("eth_getBlockByNumber", 
                                       [block_identifier, include_transactions])
        
    def close(self):
        """Clean up connections."""
        if self.session:
            self.session.close()
            
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected
        
    @property
    def chain_id(self) -> Optional[int]:
        """Get cached chain ID."""
        return self._chain_id
        
    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            latest_block = await self.get_latest_block_number()
            return latest_block is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False