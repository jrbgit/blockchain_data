#!/usr/bin/env python3
"""
Multi-Chain CLI Convenience Script

This script provides easy access to the multi-chain CLI interface.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

if __name__ == "__main__":
    from src.cli.multichain_cli import main
    import asyncio
    sys.exit(asyncio.run(main()))
