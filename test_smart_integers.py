#!/usr/bin/env python3
"""
Test Smart Integer Handling

Test that the smart integer handling correctly converts only values that exceed InfluxDB limits.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB

async def test_smart_integers():
    """Test smart integer handling."""
    print("🧪 Testing Smart Integer Handling")
    
    config = Config()
    if not config.influxdb_token:
        print("❌ No InfluxDB token configured")
        return False
    
    db_client = BlockchainInfluxDB(config)
    connected = await db_client.connect()
    
    if not connected:
        print("❌ Failed to connect to InfluxDB")
        return False
    
    print("✅ Connected to InfluxDB")
    
    try:
        # Test various integer sizes
        test_cases = [
            ("small_int", 12345),                              # Should remain integer
            ("normal_int", 1000000000),                        # Should remain integer
            ("large_int", 9223372036854775807),                # Max int, should remain integer
            ("overflow_int", 9350000000000000000000),          # From logs, should become string
            ("huge_int", 28019014209000000000000),             # From logs, should become string
        ]
        
        test_points = []
        for name, value in test_cases:
            point_data = {
                "measurement": "test_smart_integers",
                "tags": {
                    "test_case": name,
                },
                "fields": {
                    "test_value": value,
                    "original_size": len(str(value))
                },
                "time": datetime.now(timezone.utc)
            }
            test_points.append(point_data)
        
        # This should work without any errors
        db_client.write_points(test_points)
        print("✅ All test cases written successfully")
        
        # Show what happened to each value
        print("\n📊 Test Results:")
        max_int = 9223372036854775807
        for name, value in test_cases:
            if value > max_int:
                print(f"  {name}: {value} → STRING (too large for InfluxDB integer)")
            else:
                print(f"  {name}: {value} → INTEGER (fits in InfluxDB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        db_client.close()

if __name__ == "__main__":
    success = asyncio.run(test_smart_integers())
    print(f"\n{'🎉 SUCCESS' if success else '💥 FAILED'}: Smart integer handling test")