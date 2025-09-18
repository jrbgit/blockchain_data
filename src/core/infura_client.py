"""
Infura Client for Multi-Chain Blockchain Data Access

This module provides a specialized client for connecting to multiple blockchain networks
through Infura's infrastructure, with proper rate limiting and connection management.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from asyncio_throttle import Throttler
import os

from .config import Config

logger = logging.getLogger(__name__)

class InfuraClient:
    """
    Manages connections to multiple blockchain networks through Infura.
    Handles rate limiting, failover, and connection pooling across chains.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.project_id = os.getenv('INFURA_PROJECT_ID')
        if not self.project_id:
            raise ValueError("INFURA_PROJECT_ID environment variable is required")
            
        # Rate limiting (Infura allows 100k requests/day, ~1.15 req/sec sustained)
        self.throttler = Throttler(rate_limit=10, period=1.0)  # 10 req/sec burst
        
        # Connection sessions per chain
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.ws_connections: Dict[str, aiohttp.ClientWebSocketResponse] = {}
        
        # Chain configuration
        self.chains = self._get_enabled_chains()
        
        # Connection timeouts
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        logger.info(f"Initialized Infura client for {len(self.chains)} chains")
    
    def _get_enabled_chains(self) -> Dict[str, Dict[str, Any]]:
        """Get enabled chains that use Infura provider"""
        enabled_chains = {}
        
        for chain_id, chain_config in self.config.chains.items():
            if (chain_config.get('enabled', False) and 
                chain_config.get('provider') == 'infura'):
                enabled_chains[chain_id] = chain_config
                
        return enabled_chains
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Initialize HTTP sessions for all chains"""
        connector = aiohttp.TCPConnector(
            limit=50,  # Total connection pool size
            limit_per_host=10,  # Per-host connection limit
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        for chain_id, chain_config in self.chains.items():
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'GLQ-Analytics/1.0'
                }
            )
            self.sessions[chain_id] = session
            
        logger.info(f"Connected to {len(self.sessions)} Infura chains")
    
    async def close(self):
        """Close all connections"""
        # Close WebSocket connections
        for chain_id, ws in self.ws_connections.items():
            if not ws.closed:
                await ws.close()
                logger.debug(f"Closed WebSocket connection for {chain_id}")
        
        # Close HTTP sessions
        for chain_id, session in self.sessions.items():
            await session.close()
            logger.debug(f"Closed HTTP session for {chain_id}")
        
        self.sessions.clear()
        self.ws_connections.clear()
    
    def _get_rpc_url(self, chain_id: str) -> str:
        """Get the RPC URL for a chain with project ID substitution"""
        chain_config = self.chains[chain_id]
        return chain_config['rpc_url'].format(INFURA_PROJECT_ID=self.project_id)
    
    def _get_ws_url(self, chain_id: str) -> str:
        """Get the WebSocket URL for a chain with project ID substitution"""
        chain_config = self.chains[chain_id]
        return chain_config['ws_url'].format(INFURA_PROJECT_ID=self.project_id)
    
    async def make_request(self, chain_id: str, method: str, params: List[Any] = None) -> Dict[str, Any]:
        """
        Make a JSON-RPC request to a specific chain
        
        Args:
            chain_id: Chain identifier (e.g., 'ethereum', 'polygon')
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            JSON-RPC response
        """
        if chain_id not in self.chains:
            raise ValueError(f"Chain '{chain_id}' not supported or not enabled")
        
        if chain_id not in self.sessions:
            raise RuntimeError("Client not connected. Use 'async with InfuraClient()' or call connect()")
        
        # Rate limiting
        async with self.throttler:
            session = self.sessions[chain_id]
            url = self._get_rpc_url(chain_id)
            
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or [],
                "id": 1
            }
            
            try:
                async with session.post(url, json=payload) as response:
                    response_data = await response.json()
                    
                    if response.status != 200:
                        logger.error(f"HTTP error {response.status} for {chain_id}: {response_data}")
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                    
                    if 'error' in response_data:
                        logger.error(f"RPC error for {chain_id}: {response_data['error']}")
                        raise Exception(f"RPC Error: {response_data['error']}")
                    
                    return response_data.get('result')
                    
            except asyncio.TimeoutError:
                logger.error(f"Timeout for {chain_id} request: {method}")
                raise
            except Exception as e:
                logger.error(f"Request failed for {chain_id}: {str(e)}")
                raise
    
    async def get_latest_block_number(self, chain_id: str) -> int:
        """Get the latest block number for a chain"""
        result = await self.make_request(chain_id, "eth_blockNumber")
        return int(result, 16)
    
    async def get_block_by_number(self, chain_id: str, block_number: int, full_transactions: bool = True) -> Dict[str, Any]:
        """Get block data by number"""
        hex_number = hex(block_number)
        result = await self.make_request(chain_id, "eth_getBlockByNumber", [hex_number, full_transactions])
        return result
    
    async def get_block_by_hash(self, chain_id: str, block_hash: str, full_transactions: bool = True) -> Dict[str, Any]:
        """Get block data by hash"""
        result = await self.make_request(chain_id, "eth_getBlockByHash", [block_hash, full_transactions])
        return result
    
    async def get_transaction_receipt(self, chain_id: str, tx_hash: str) -> Dict[str, Any]:
        """Get transaction receipt"""
        result = await self.make_request(chain_id, "eth_getTransactionReceipt", [tx_hash])
        return result
    
    async def get_chain_id(self, chain_id: str) -> int:
        """Get the chain ID from the blockchain"""
        result = await self.make_request(chain_id, "eth_chainId")
        return int(result, 16)
    
    async def batch_request(self, chain_id: str, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Make multiple requests in a single batch for better performance
        
        Args:
            chain_id: Chain identifier
            requests: List of request dictionaries with 'method' and 'params'
            
        Returns:
            List of responses
        """
        if chain_id not in self.chains:
            raise ValueError(f"Chain '{chain_id}' not supported or not enabled")
            
        if chain_id not in self.sessions:
            raise RuntimeError("Client not connected")
        
        # Rate limiting for batch requests
        async with self.throttler:
            session = self.sessions[chain_id]
            url = self._get_rpc_url(chain_id)
            
            # Prepare batch payload
            batch_payload = []
            for i, req in enumerate(requests):
                payload = {
                    "jsonrpc": "2.0",
                    "method": req["method"],
                    "params": req.get("params", []),
                    "id": i + 1
                }
                batch_payload.append(payload)
            
            try:
                async with session.post(url, json=batch_payload) as response:
                    response_data = await response.json()
                    
                    if response.status != 200:
                        logger.error(f"Batch HTTP error {response.status} for {chain_id}")
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                    
                    # Sort responses by ID to maintain order
                    responses = sorted(response_data, key=lambda x: x.get('id', 0))
                    results = []
                    
                    for resp in responses:
                        if 'error' in resp:
                            logger.warning(f"Batch RPC error for {chain_id}: {resp['error']}")
                            results.append(None)  # or raise exception based on requirements
                        else:
                            results.append(resp.get('result'))
                    
                    return results
                    
            except Exception as e:
                logger.error(f"Batch request failed for {chain_id}: {str(e)}")
                raise
    
    async def connect_websocket(self, chain_id: str) -> aiohttp.ClientWebSocketResponse:
        """
        Connect to WebSocket for real-time data
        
        Args:
            chain_id: Chain identifier
            
        Returns:
            WebSocket connection
        """
        if chain_id not in self.chains:
            raise ValueError(f"Chain '{chain_id}' not supported or not enabled")
        
        ws_url = self._get_ws_url(chain_id)
        session = self.sessions[chain_id]
        
        try:
            ws = await session.ws_connect(ws_url)
            self.ws_connections[chain_id] = ws
            logger.info(f"Connected to WebSocket for {chain_id}")
            return ws
        except Exception as e:
            logger.error(f"Failed to connect WebSocket for {chain_id}: {str(e)}")
            raise
    
    async def subscribe_to_new_blocks(self, chain_id: str) -> aiohttp.ClientWebSocketResponse:
        """Subscribe to new block headers via WebSocket"""
        ws = await self.connect_websocket(chain_id)
        
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "eth_subscribe",
            "params": ["newHeads"],
            "id": 1
        }
        
        await ws.send_str(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to new blocks for {chain_id}")
        return ws
    
    async def get_chain_info(self, chain_id: str) -> Dict[str, Any]:
        """Get basic chain information"""
        try:
            chain_id_actual = await self.get_chain_id(chain_id)
            latest_block = await self.get_latest_block_number(chain_id)
            
            chain_config = self.chains[chain_id]
            
            return {
                'chain_name': chain_config['name'],
                'chain_id': chain_id_actual,
                'expected_chain_id': chain_config['chain_id'],
                'latest_block': latest_block,
                'provider': 'infura',
                'connected': True
            }
        except Exception as e:
            logger.error(f"Failed to get chain info for {chain_id}: {str(e)}")
            return {
                'chain_name': self.chains[chain_id]['name'],
                'chain_id': None,
                'latest_block': None,
                'provider': 'infura',
                'connected': False,
                'error': str(e)
            }
    
    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """Check the health of all chain connections"""
        health_status = {}
        
        for chain_id in self.chains.keys():
            try:
                info = await self.get_chain_info(chain_id)
                health_status[chain_id] = {
                    'status': 'healthy' if info['connected'] else 'unhealthy',
                    'info': info
                }
            except Exception as e:
                health_status[chain_id] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        return health_status