#!/usr/bin/env python3
"""
Simple test script for GLQ Chain Monitoring Service
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from processors.monitoring_service import MonitoringService
from core.config import Config

async def test_service():
    """Test the monitoring service startup."""
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = Config()
    
    # Create service
    service = MonitoringService(config, port=8001)
    
    try:
        logger.info("Starting monitoring service...")
        await service.start_service()
        logger.info("Service started on http://localhost:8001/dashboard")
        logger.info("Press Ctrl+C to stop")
        
        # Run for a limited time or until interrupted
        await asyncio.sleep(60)  # Run for 60 seconds max
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        logger.info("Shutting down...")
        await service.shutdown()
        logger.info("Done")

if __name__ == "__main__":
    try:
        asyncio.run(test_service())
    except KeyboardInterrupt:
        print("\nStopped by user")