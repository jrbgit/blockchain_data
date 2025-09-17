#!/usr/bin/env python3
"""
Startup script for GLQ Chain Real-time Monitoring Service
Provides a web dashboard at http://localhost:8000
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from processors.monitoring_service import main

if __name__ == "__main__":
    print("🚀 Starting GLQ Chain Monitoring Service...")
    print("📊 Dashboard will be available at: http://localhost:8001/dashboard")
    print("🔧 API available at: http://localhost:8001/api/status")
    print("❤️  Health check: http://localhost:8001/health")
    print("")
    print("Press Ctrl+C to stop the service")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Service stopped by user")
    except Exception as e:
        print(f"\n❌ Service error: {e}")