#!/usr/bin/env python3
"""
Quick test script for multichain CLI functionality
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and show result"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Exit code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out (30s)")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def main():
    print("🧪 Testing Multi-Chain CLI Commands")
    print("This will test basic CLI functionality")
    
    # Test commands
    tests = [
        ("multichain.bat --help", "CLI help display"),
        ("multichain.bat status", "System status check"),
        ("python start_multichain_monitor.py --help", "Monitor help display"),
    ]
    
    results = []
    
    for cmd, desc in tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    for desc, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {desc}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All CLI tests passed!")
    else:
        print("⚠️ Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()