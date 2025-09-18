"""
Multi-Chain Blockchain Client

This module provides a unified interface for interacting with multiple blockchain networks,
including the local GLQ chain and external chains via Infura.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import os

from .config import Config
from .blockchain_client import BlockchainClient
from .infura_client import InfuraClient

logger = logging.getLogger(__name__)

class MultiChainClient:
    """
    Unified client for interacting with multiple blockchain networks.
    Manages both local chains (GLQ) and external chains (Infura).
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Client instances
        self.local_clients: Dict[str, BlockchainClient] = {}
        self.infura_client: Optional[InfuraClient] = None
        
        # Chain configuration
        self.chains = self._get_enabled_chains()
        
        # Connection status
        self.connected_chains: Dict[str, bool] = {}
        
        logger.info(f"Initialized multi-chain client for {len(self.chains)} chains")
    
    def _get_enabled_chains(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled chains from configuration"""
        enabled_chains = {}
        
        for chain_id, chain_config in self.config.chains.items():
            if chain_config.get('enabled', False):
                enabled_chains[chain_id] = chain_config
                
        return enabled_chains
    
    async def connect(self):
        """Connect to all enabled chains"""
        connection_tasks = []
        
        # Separate local and Infura chains
        local_chains = {k: v for k, v in self.chains.items() if v.get('provider') != 'infura'}
        infura_chains = {k: v for k, v in self.chains.items() if v.get('provider') == 'infura'}
        
        # Initialize local clients
        for chain_id, chain_config in local_chains.items():
            try:
                client = BlockchainClient(
                    config_or_rpc_url=chain_config['rpc_url'],
                    ws_url=chain_config.get('ws_url'),
                    max_connections=20,
                    timeout=30
                )
                self.local_clients[chain_id] = client
                connection_tasks.append(self._connect_local_chain(chain_id, client))
            except Exception as e:
                logger.error(f"Failed to initialize local client for {chain_id}: {e}")
        
        # Initialize Infura client if needed
        if infura_chains:
            try:
                self.infura_client = InfuraClient(self.config)
                connection_tasks.append(self._connect_infura_chains())
            except Exception as e:
                logger.error(f"Failed to initialize Infura client: {e}")
        
        # Execute all connections concurrently
        if connection_tasks:
            await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Log connection status
        connected_count = sum(self.connected_chains.values())
        total_count = len(self.chains)
        logger.info(f"Connected to {connected_count}/{total_count} chains")
        
        for chain_id, status in self.connected_chains.items():
            chain_name = self.chains[chain_id]['name']
            status_str = "[OK]" if status else "[FAIL]"
            logger.info(f"  {status_str} {chain_name} ({chain_id})")
    
    async def _connect_local_chain(self, chain_id: str, client: BlockchainClient):
        """Connect to a local blockchain"""
        try:
            success = await client.connect()
            self.connected_chains[chain_id] = success
            
            if success:
                logger.info(f"Connected to local chain: {self.chains[chain_id]['name']}")
            else:
                logger.warning(f"Failed to connect to local chain: {chain_id}")
                
        except Exception as e:
            logger.error(f"Error connecting to local chain {chain_id}: {e}")
            self.connected_chains[chain_id] = False
    
    async def _connect_infura_chains(self):
        """Connect to all Infura chains"""
        try:
            await self.infura_client.connect()
            
            # Check health of all Infura chains
            health_status = await self.infura_client.health_check()
            
            for chain_id, health in health_status.items():
                self.connected_chains[chain_id] = health['status'] == 'healthy'
                
                if health['status'] == 'healthy':
                    logger.info(f"Connected to Infura chain: {self.chains[chain_id]['name']}")
                else:
                    logger.warning(f"Failed to connect to Infura chain: {chain_id} - {health.get('error', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Error connecting to Infura chains: {e}")
            # Mark all Infura chains as disconnected
            infura_chains = {k: v for k, v in self.chains.items() if v.get('provider') == 'infura'}
            for chain_id in infura_chains.keys():
                self.connected_chains[chain_id] = False
    
    async def close(self):
        """Close all connections"""
        # Close local clients
        for chain_id, client in self.local_clients.items():
            try:
                client.close()
                logger.debug(f"Closed local client for {chain_id}")
            except Exception as e:
                logger.error(f"Error closing local client {chain_id}: {e}")
        
        # Close Infura client
        if self.infura_client:
            try:
                await self.infura_client.close()
                logger.debug("Closed Infura client")
            except Exception as e:
                logger.error(f"Error closing Infura client: {e}")
        
        self.local_clients.clear()
        self.infura_client = None
        self.connected_chains.clear()
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _get_client(self, chain_id: str):
        """Get the appropriate client for a chain"""
        if chain_id not in self.chains:
            raise ValueError(f"Chain '{chain_id}' not configured or not enabled")
        
        if not self.connected_chains.get(chain_id, False):
            raise RuntimeError(f"Chain '{chain_id}' is not connected")
        
        chain_config = self.chains[chain_id]
        
        if chain_config.get('provider') == 'infura':
            if not self.infura_client:
                raise RuntimeError("Infura client not initialized")
            return self.infura_client
        else:
            if chain_id not in self.local_clients:
                raise RuntimeError(f"Local client for '{chain_id}' not initialized")
            return self.local_clients[chain_id]
    
    # Unified blockchain query methods
    async def get_latest_block_number(self, chain_id: str) -> Optional[int]:
        """Get latest block number for a specific chain"""
        client = self._get_client(chain_id)
        
        if isinstance(client, InfuraClient):
            return await client.get_latest_block_number(chain_id)
        else:
            return await client.get_latest_block_number()
    
    async def get_block(self, chain_id: str, block_number: Union[int, str], 
                       include_transactions: bool = True) -> Optional[Dict[str, Any]]:
        """Get block data for a specific chain"""
        client = self._get_client(chain_id)
        
        if isinstance(client, InfuraClient):
            if isinstance(block_number, int):
                return await client.get_block_by_number(chain_id, block_number, include_transactions)
            else:
                return await client.get_block_by_hash(chain_id, block_number, include_transactions)
        else:
            return await client.get_block(block_number, include_transactions)
    
    async def get_transaction_receipt(self, chain_id: str, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt for a specific chain"""
        client = self._get_client(chain_id)
        
        if isinstance(client, InfuraClient):
            return await client.get_transaction_receipt(chain_id, tx_hash)
        else:
            return await client.get_transaction_receipt(tx_hash)
    
    async def get_chain_id(self, chain_id: str) -> Optional[int]:
        """Get the actual chain ID from the blockchain"""
        client = self._get_client(chain_id)
        
        if isinstance(client, InfuraClient):
            return await client.get_chain_id(chain_id)
        else:
            return await client.get_chain_id()
    
    async def get_logs(self, chain_id: str, from_block: int, to_block: int, 
                      addresses: List[str] = None, topics: List[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get logs/events for block range on a specific chain"""
        client = self._get_client(chain_id)
        
        if isinstance(client, InfuraClient):
            # For Infura, we need to use the make_request method
            filter_params = {
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block)
            }
            
            if addresses:
                filter_params["address"] = addresses
            if topics:
                filter_params["topics"] = topics
            
            return await client.make_request(chain_id, "eth_getLogs", [filter_params])
        else:
            return await client.get_logs(from_block, to_block, addresses, topics)
    
    async def batch_get_blocks(self, chain_id: str, start_block: int, end_block: int) -> List[Optional[Dict[str, Any]]]:
        """Get multiple blocks in batch for better performance"""
        client = self._get_client(chain_id)
        
        if isinstance(client, InfuraClient):
            # Create batch requests
            requests = []
            for block_num in range(start_block, end_block + 1):
                requests.append({
                    "method": "eth_getBlockByNumber",
                    "params": [hex(block_num), True]
                })
            
            return await client.batch_request(chain_id, requests)
        else:
            return await client.get_blocks_batch(start_block, end_block)
    
    # Multi-chain operations
    async def get_latest_blocks_all_chains(self) -> Dict[str, Optional[int]]:
        """Get latest block numbers for all connected chains"""
        results = {}
        tasks = []
        
        for chain_id in self.connected_chains.keys():
            if self.connected_chains[chain_id]:
                tasks.append(self._get_latest_block_with_chain_id(chain_id))
        
        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for chain_id, response in zip(self.connected_chains.keys(), responses):
                if isinstance(response, Exception):
                    logger.error(f"Error getting latest block for {chain_id}: {response}")
                    results[chain_id] = None
                else:
                    results[chain_id] = response
        
        return results
    
    async def _get_latest_block_with_chain_id(self, chain_id: str) -> Optional[int]:
        """Helper method for getting latest block with chain ID"""
        try:
            return await self.get_latest_block_number(chain_id)
        except Exception as e:
            logger.error(f"Error getting latest block for {chain_id}: {e}")
            return None
    
    async def get_chain_info_all(self) -> Dict[str, Dict[str, Any]]:
        """Get chain information for all connected chains"""
        results = {}
        
        for chain_id in self.chains.keys():
            try:
                if self.connected_chains.get(chain_id, False):
                    latest_block = await self.get_latest_block_number(chain_id)
                    actual_chain_id = await self.get_chain_id(chain_id)
                    
                    chain_config = self.chains[chain_id]
                    results[chain_id] = {
                        'name': chain_config['name'],
                        'chain_id': actual_chain_id,
                        'expected_chain_id': chain_config['chain_id'],
                        'latest_block': latest_block,
                        'provider': chain_config.get('provider', 'local'),
                        'connected': True
                    }
                else:
                    chain_config = self.chains[chain_id]
                    results[chain_id] = {
                        'name': chain_config['name'],
                        'chain_id': None,
                        'expected_chain_id': chain_config['chain_id'],
                        'latest_block': None,
                        'provider': chain_config.get('provider', 'local'),
                        'connected': False
                    }
            except Exception as e:
                logger.error(f"Error getting chain info for {chain_id}: {e}")
                results[chain_id] = {
                    'name': self.chains[chain_id]['name'],
                    'connected': False,
                    'error': str(e)
                }
        
        return results
    
    # Chain management
    def get_enabled_chains(self) -> List[str]:
        """Get list of enabled chain IDs"""
        return list(self.chains.keys())
    
    def get_connected_chains(self) -> List[str]:
        """Get list of currently connected chain IDs"""
        return [chain_id for chain_id, connected in self.connected_chains.items() if connected]
    
    def is_chain_connected(self, chain_id: str) -> bool:
        """Check if a specific chain is connected"""
        return self.connected_chains.get(chain_id, False)
    
    def get_chain_config(self, chain_id: str) -> Dict[str, Any]:
        """Get configuration for a specific chain"""
        if chain_id not in self.chains:
            raise ValueError(f"Chain '{chain_id}' not configured")
        return self.chains[chain_id]
    
    # Health monitoring
    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all chains"""
        health_status = {}
        
        for chain_id in self.chains.keys():
            try:
                if self.connected_chains.get(chain_id, False):
                    latest_block = await self.get_latest_block_number(chain_id)
                    health_status[chain_id] = {
                        'status': 'healthy',
                        'latest_block': latest_block,
                        'chain_name': self.chains[chain_id]['name']
                    }
                else:
                    health_status[chain_id] = {
                        'status': 'disconnected',
                        'chain_name': self.chains[chain_id]['name']
                    }
            except Exception as e:
                health_status[chain_id] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'chain_name': self.chains[chain_id]['name']
                }
        
        return health_status
    
    # WebSocket support
    async def subscribe_to_new_blocks(self, chain_id: str):
        """Subscribe to new block notifications for a chain"""
        client = self._get_client(chain_id)
        
        if isinstance(client, InfuraClient):
            return await client.subscribe_to_new_blocks(chain_id)
        else:
            # For local chains, WebSocket subscription would need to be implemented
            # in the BlockchainClient class
            raise NotImplementedError("WebSocket subscription not implemented for local chains")