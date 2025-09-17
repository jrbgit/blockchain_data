#!/usr/bin/env python3
"""
Startup script for GLQ Chain Command-line Real-time Monitor
Displays real-time blockchain monitoring in the terminal
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from processors.realtime_monitor import main

if __name__ == "__main__":
    print("🔗 Starting GLQ Chain Command-line Monitor...")
    print("📊 Real-time blockchain monitoring with live display")
    print("🔄 Monitors new blocks as they arrive on GLQ Chain")
    print("💾 Automatically stores data in InfluxDB")
    print("")
    print("Press Ctrl+C to stop monitoring")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped by user")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")