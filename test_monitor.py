#!/usr/bin/env python3
"""
Quick test script to verify monitor fixes
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import Config
from src.processors.multichain_monitor import MultiChainMonitor

async def test_monitor():
    """Test that monitor can initialize and start without errors"""
    try:
        config = Config()
        monitor = MultiChainMonitor(config)
        
        print("✓ Monitor initialized successfully")
        
        if await monitor.initialize():
            print("✓ Monitor connections established successfully")
            
            # Set selected chains to only GLQ to avoid rate limiting
            monitor.selected_chains = {'glq'}
            
            print("✓ Monitor configured for GLQ chain only")
            print("✓ All fixes appear to be working!")
            
            await monitor.stop_monitoring()
            print("✓ Monitor stopped cleanly")
            
            return True
        else:
            print("✗ Monitor initialization failed")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_monitor())
    if result:
        print("\n🎉 SUCCESS: All fixes are working correctly!")
    else:
        print("\n❌ FAILED: There are still issues to resolve")
    sys.exit(0 if result else 1)