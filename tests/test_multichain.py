"""
Multi-Chain Connectivity Test

This script tests the new multi-chain functionality including:
- Configuration loading
- Infura client connections
- Multi-chain client operations
- Basic blockchain data retrieval across chains
"""

import asyncio
import logging
import os
from typing import Dict, Any
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / \"src\"))

from src.core.config import Config
from src.core.infura_client import InfuraClient
from src.core.multichain_client import MultiChainClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/multichain_test.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_config_loading():
    """Test configuration loading"""
    logger.info("🔧 Testing configuration loading...")
    
    try:
        config = Config()
        
        # Check if chains are loaded
        if not hasattr(config, 'chains') or not config.chains:
            logger.error("❌ No chains configuration found")
            return False
            
        logger.info(f"✅ Configuration loaded successfully")
        logger.info(f"📋 Found {len(config.chains)} configured chains:")
        
        for chain_id, chain_config in config.chains.items():
            status = "✅" if chain_config.get('enabled', False) else "⏸️"
            provider = chain_config.get('provider', 'unknown')
            logger.info(f"   {status} {chain_config['name']} ({chain_id}) - {provider}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration loading failed: {e}")
        return False

async def test_infura_client():
    """Test Infura client connectivity"""
    logger.info("🌐 Testing Infura client...")
    
    try:
        # Check environment variable
        project_id = os.getenv('INFURA_PROJECT_ID')
        if not project_id:
            logger.error("❌ INFURA_PROJECT_ID environment variable not set")
            return False
            
        logger.info(f"🔑 Using Infura Project ID: {project_id[:8]}...")
        
        config = Config()
        
        async with InfuraClient(config) as infura_client:
            logger.info(f"✅ Infura client initialized for {len(infura_client.chains)} chains")
            
            # Test health check
            health_status = await infura_client.health_check()
            
            logger.info("🏥 Health check results:")
            for chain_id, health in health_status.items():
                status_icon = "✅" if health['status'] == 'healthy' else "❌"
                chain_name = health['info']['chain_name'] if 'info' in health else chain_id
                
                if health['status'] == 'healthy':
                    latest_block = health['info']['latest_block']
                    actual_chain_id = health['info']['chain_id']
                    logger.info(f"   {status_icon} {chain_name}: Chain ID {actual_chain_id}, Latest Block {latest_block:,}")
                else:
                    error = health.get('error', 'Unknown error')
                    logger.warning(f"   {status_icon} {chain_name}: {error}")
            
            # Test individual chain calls
            logger.info("🧪 Testing individual chain calls...")
            
            for chain_id in ['ethereum', 'polygon', 'base']:  # Test a few chains
                if chain_id in health_status and health_status[chain_id]['status'] == 'healthy':
                    try:
                        latest_block = await infura_client.get_latest_block_number(chain_id)
                        block_data = await infura_client.get_block_by_number(chain_id, latest_block - 1)  # Get previous block for stability
                        
                        if block_data:
                            tx_count = len(block_data.get('transactions', []))
                            logger.info(f"   ✅ {chain_id}: Block {latest_block-1} has {tx_count} transactions")
                        else:
                            logger.warning(f"   ⚠️ {chain_id}: Could not retrieve block data")
                            
                    except Exception as e:
                        logger.error(f"   ❌ {chain_id}: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Infura client test failed: {e}")
        return False

async def test_multichain_client():
    """Test multi-chain client"""
    logger.info("🔗 Testing multi-chain client...")
    
    try:
        config = Config()
        
        async with MultiChainClient(config) as multi_client:
            logger.info("✅ Multi-chain client initialized")
            
            # Get connection status
            enabled_chains = multi_client.get_enabled_chains()
            connected_chains = multi_client.get_connected_chains()
            
            logger.info(f"📊 Chain Status: {len(connected_chains)}/{len(enabled_chains)} chains connected")
            
            # Get chain info for all chains
            chain_info = await multi_client.get_chain_info_all()
            
            logger.info("📋 Chain Information:")
            for chain_id, info in chain_info.items():
                if info.get('connected', False):
                    latest_block = info.get('latest_block', 'Unknown')
                    chain_id_actual = info.get('chain_id', 'Unknown')
                    provider = info.get('provider', 'unknown')
                    logger.info(f"   ✅ {info['name']} ({chain_id}): Chain ID {chain_id_actual}, Block {latest_block:,} via {provider}")
                else:
                    error = info.get('error', 'Connection failed')
                    logger.warning(f"   ❌ {info['name']} ({chain_id}): {error}")
            
            # Test cross-chain latest blocks
            logger.info("🌐 Testing cross-chain operations...")
            
            latest_blocks = await multi_client.get_latest_blocks_all_chains()
            logger.info("📈 Latest blocks across all chains:")
            
            for chain_id, latest_block in latest_blocks.items():
                if latest_block is not None:
                    chain_name = chain_info[chain_id]['name']
                    logger.info(f"   {chain_name}: {latest_block:,}")
                else:
                    chain_name = chain_info.get(chain_id, {}).get('name', chain_id)
                    logger.warning(f"   {chain_name}: Failed to get latest block")
            
            # Test health check
            logger.info("🏥 Multi-chain health check...")
            health_status = await multi_client.health_check()
            
            healthy_count = sum(1 for status in health_status.values() if status.get('status') == 'healthy')
            total_count = len(health_status)
            
            logger.info(f"✅ Health check completed: {healthy_count}/{total_count} chains healthy")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Multi-chain client test failed: {e}")
        return False

async def test_batch_operations():
    """Test batch operations for performance"""
    logger.info("⚡ Testing batch operations...")
    
    try:
        config = Config()
        
        async with MultiChainClient(config) as multi_client:
            connected_chains = multi_client.get_connected_chains()
            
            if not connected_chains:
                logger.warning("⚠️ No chains connected, skipping batch tests")
                return True
            
            # Test batch block retrieval on first connected chain
            test_chain = connected_chains[0]
            chain_name = multi_client.get_chain_config(test_chain)['name']
            
            logger.info(f"🧪 Testing batch operations on {chain_name}...")
            
            latest_block = await multi_client.get_latest_block_number(test_chain)
            start_block = max(1, latest_block - 5)  # Get last 5 blocks
            
            logger.info(f"📦 Fetching blocks {start_block} to {latest_block}...")
            
            import time
            start_time = time.time()
            
            blocks = await multi_client.batch_get_blocks(test_chain, start_block, latest_block)
            
            end_time = time.time()
            duration = end_time - start_time
            
            successful_blocks = sum(1 for block in blocks if block is not None)
            total_blocks = len(blocks)
            
            logger.info(f"✅ Batch operation completed:")
            logger.info(f"   📊 Retrieved {successful_blocks}/{total_blocks} blocks in {duration:.2f}s")
            logger.info(f"   ⚡ Average: {duration/total_blocks:.3f}s per block")
            
            # Show some block info
            for i, block in enumerate(blocks):
                if block:
                    block_num = start_block + i
                    tx_count = len(block.get('transactions', []))
                    timestamp = int(block.get('timestamp', '0x0'), 16)
                    logger.info(f"   📋 Block {block_num}: {tx_count} transactions, timestamp {timestamp}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Batch operations test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 Starting multi-chain connectivity tests...")
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    tests = [
        ("Configuration Loading", test_config_loading()),
        ("Infura Client", test_infura_client()),
        ("Multi-Chain Client", test_multichain_client()),
        ("Batch Operations", test_batch_operations()),
    ]
    
    results = {}
    
    for test_name, test_coro in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_coro
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"💥 {test_name}: CRASHED - {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("📊 TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\n🏁 Overall Result: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        logger.info("🎉 All tests passed! Multi-chain setup is ready.")
        return True
    else:
        logger.error(f"💥 {total_count - passed_count} test(s) failed. Please check the logs.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
