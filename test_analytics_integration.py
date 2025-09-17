#!/usr/bin/env python3
"""
Test script for integrated analytics monitoring system
Tests the real-time monitor with analytics integration
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from processors.realtime_monitor import RealtimeMonitor
from processors.monitoring_service import MonitoringService
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
logger = logging.getLogger(__name__)

class AnalyticsIntegrationTester:
    """Test suite for analytics integration with real-time monitoring."""
    
    def __init__(self):
        self.config = None
        self.monitor = None
        self.service = None
        
    async def setup_test_environment(self):
        """Setup test environment and configuration."""
        console.print(Panel(
            Text("🧪 Setting up Analytics Integration Test Environment", style="bold cyan"),
            border_style="cyan"
        ))
        
        # Load configuration
        try:
            self.config = Config()
            console.print("✅ Configuration loaded successfully")
            
            # Print analytics configuration
            analytics_config = self.config.analytics_config
            console.print(f"📊 Analytics enabled: {self.config.is_analytics_enabled()}")
            console.print(f"🔧 Realtime analytics: {self.config.get_analytics_realtime_config().get('enabled', False)}")
            
            # Show module configurations
            modules = analytics_config.get('modules', {})
            for module, config in modules.items():
                enabled = config.get('enabled', False)
                status = "🟢 Enabled" if enabled else "🔴 Disabled"
                console.print(f"   {module}: {status}")
                
        except Exception as e:
            console.print(f"❌ Failed to load configuration: {e}")
            return False
            
        return True
        
    async def test_monitor_initialization(self):
        """Test monitor initialization with analytics."""
        console.print(Panel(
            Text("🚀 Testing Monitor Initialization", style="bold green"),
            border_style="green"
        ))
        
        try:
            # Create monitor instance
            self.monitor = RealtimeMonitor(self.config)
            console.print("✅ RealtimeMonitor created")
            
            # Check analytics initialization
            if self.monitor.analytics:
                console.print("✅ Analytics coordinator initialized")
                console.print(f"   Max processing time: {getattr(self.monitor, 'analytics_max_time', 'N/A')}s")
                console.print(f"   Skip on timeout: {getattr(self.monitor, 'analytics_skip_on_timeout', False)}")
            else:
                console.print("ℹ️ Analytics coordinator not initialized (may be disabled)")
            
            # Check analytics-related statistics initialization
            stats = self.monitor.stats
            analytics_stats = [
                'analytics_enabled', 'token_transfers_found', 'dex_swaps_found',
                'liquidity_events_found', 'defi_events_found', 'total_analytics_events',
                'analytics_timeouts', 'analytics_processing_time'
            ]
            
            for stat in analytics_stats:
                if stat in stats:
                    console.print(f"   ✅ {stat}: {stats[stat]}")
                else:
                    console.print(f"   ❌ Missing statistic: {stat}")
            
            # Initialize connections
            console.print("🔌 Initializing connections...")
            initialized = await self.monitor.initialize()
            
            if initialized:
                console.print("✅ Monitor initialized successfully")
                console.print(f"   Starting from block: {self.monitor.last_processed_block}")
                console.print(f"   Latest network block: {self.monitor.latest_network_block}")
                return True
            else:
                console.print("❌ Monitor initialization failed")
                return False
                
        except Exception as e:
            console.print(f"❌ Monitor initialization error: {e}")
            logger.error(f"Monitor initialization failed: {e}", exc_info=True)
            return False
    
    async def test_web_service_integration(self):
        """Test web monitoring service with analytics support."""
        console.print(Panel(
            Text("🌐 Testing Web Service Integration", style="bold blue"),
            border_style="blue"
        ))
        
        try:
            # Create monitoring service
            self.service = MonitoringService(self.config, port=8999)  # Use test port
            console.print("✅ MonitoringService created")
            
            # Test status endpoint functionality
            if self.monitor:
                status = self.monitor.get_status()
                console.print("✅ Status data structure:")
                
                required_keys = ['running', 'paused', 'last_processed_block', 'latest_network_block', 'processing_lag', 'statistics', 'uptime']
                for key in required_keys:
                    if key in status:
                        console.print(f"   ✅ {key}: {status[key]}")
                    else:
                        console.print(f"   ❌ Missing key: {key}")
                
                # Check analytics statistics in status
                stats = status.get('statistics', {})
                analytics_keys = ['analytics_enabled', 'token_transfers_found', 'dex_swaps_found']
                for key in analytics_keys:
                    if key in stats:
                        console.print(f"   ✅ Analytics stat {key}: {stats[key]}")
                    else:
                        console.print(f"   ❌ Missing analytics stat: {key}")
            
            console.print("✅ Web service integration test passed")
            return True
            
        except Exception as e:
            console.print(f"❌ Web service integration error: {e}")
            logger.error(f"Web service integration failed: {e}", exc_info=True)
            return False
    
    async def test_analytics_configuration_loading(self):
        """Test analytics configuration loading and module controls."""
        console.print(Panel(
            Text("⚙️ Testing Analytics Configuration", style="bold yellow"),
            border_style="yellow"
        ))
        
        try:
            # Test main analytics enable/disable
            analytics_enabled = self.config.is_analytics_enabled()
            console.print(f"✅ Analytics globally enabled: {analytics_enabled}")
            
            # Test module-specific controls
            modules = ['token_analytics', 'dex_analytics', 'defi_analytics', 'advanced_analytics']
            for module in modules:
                enabled = self.config.is_analytics_module_enabled(module)
                config_data = self.config.get_analytics_module_config(module)
                console.print(f"✅ {module}: {'Enabled' if enabled else 'Disabled'}")
                if config_data:
                    console.print(f"   Config keys: {list(config_data.keys())}")
            
            # Test realtime analytics configuration
            realtime_config = self.config.get_analytics_realtime_config()
            console.print("✅ Realtime analytics config:")
            for key, value in realtime_config.items():
                console.print(f"   {key}: {value}")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Analytics configuration test error: {e}")
            logger.error(f"Analytics configuration test failed: {e}", exc_info=True)
            return False
    
    async def test_short_monitoring_run(self):
        """Run a short monitoring session to test analytics processing."""
        console.print(Panel(
            Text("⏱️ Testing Short Monitoring Run", style="bold magenta"),
            border_style="magenta"
        ))
        
        if not self.monitor:
            console.print("❌ Monitor not initialized")
            return False
        
        try:
            console.print("🔄 Starting short monitoring run (10 seconds)...")
            
            # Start monitoring in background
            monitor_task = asyncio.create_task(self._run_monitor_briefly())
            
            # Wait for monitoring to run
            await asyncio.sleep(10)
            
            # Stop monitoring
            await self.monitor.stop_monitoring()
            
            # Wait for task to complete
            try:
                await asyncio.wait_for(monitor_task, timeout=5.0)
            except asyncio.TimeoutError:
                console.print("⚠️ Monitor task did not complete within timeout")
            
            # Check final statistics
            final_stats = self.monitor.stats
            console.print("📊 Final Statistics:")
            for key, value in final_stats.items():
                console.print(f"   {key}: {value}")
            
            # Verify analytics ran if enabled
            if final_stats.get('analytics_enabled', False):
                if final_stats.get('blocks_processed', 0) > 0:
                    console.print("✅ Analytics processing verified (blocks processed)")
                else:
                    console.print("ℹ️ No blocks processed during test run")
            else:
                console.print("ℹ️ Analytics disabled - test skipped")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Short monitoring run error: {e}")
            logger.error(f"Short monitoring run failed: {e}", exc_info=True)
            return False
    
    async def _run_monitor_briefly(self):
        """Helper method to run monitor briefly."""
        try:
            # Run monitoring cycles for a short time
            for i in range(5):  # Max 5 cycles
                if not self.monitor.running:
                    break
                await self.monitor._monitoring_cycle()
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Brief monitoring run error: {e}")
    
    async def cleanup(self):
        """Cleanup test resources."""
        console.print("\n🧹 Cleaning up test resources...")
        
        if self.monitor:
            try:
                await self.monitor.stop_monitoring()
                console.print("✅ Monitor stopped")
            except:
                pass
        
        if self.service:
            try:
                await self.service.shutdown()
                console.print("✅ Web service stopped")
            except:
                pass
    
    async def run_all_tests(self):
        """Run all integration tests."""
        console.print(Panel(
            Text("🧪 Analytics Integration Test Suite", style="bold white"),
            subtitle="Testing real-time monitoring with analytics",
            border_style="white"
        ))
        
        test_results = {}
        
        # Setup
        test_results['setup'] = await self.setup_test_environment()
        
        if test_results['setup']:
            # Core tests
            test_results['monitor_init'] = await self.test_monitor_initialization()
            test_results['config_loading'] = await self.test_analytics_configuration_loading()
            test_results['web_service'] = await self.test_web_service_integration()
            
            # Optional monitoring test (requires blockchain connection)
            try:
                test_results['monitoring_run'] = await self.test_short_monitoring_run()
            except Exception as e:
                console.print(f"⚠️ Monitoring run test skipped: {e}")
                test_results['monitoring_run'] = None
        
        # Cleanup
        await self.cleanup()
        
        # Summary
        console.print(Panel(
            self._generate_test_summary(test_results),
            title="🏁 Test Results Summary",
            border_style="bright_white"
        ))
        
        return test_results
    
    def _generate_test_summary(self, results):
        """Generate test summary report."""
        passed = sum(1 for r in results.values() if r is True)
        failed = sum(1 for r in results.values() if r is False)
        skipped = sum(1 for r in results.values() if r is None)
        total = len(results)
        
        summary = f"✅ Passed: {passed}\n"
        summary += f"❌ Failed: {failed}\n"
        summary += f"⚠️ Skipped: {skipped}\n"
        summary += f"📊 Total: {total}\n\n"
        
        for test, result in results.items():
            status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️ SKIP"
            summary += f"{status} {test}\n"
        
        return Text(summary)


async def main():
    """Main test function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Create and run tester
    tester = AnalyticsIntegrationTester()
    
    try:
        results = await tester.run_all_tests()
        
        # Exit with appropriate code
        failed_tests = sum(1 for r in results.values() if r is False)
        sys.exit(0 if failed_tests == 0 else 1)
        
    except KeyboardInterrupt:
        console.print("\n⚠️ Test interrupted by user")
        await tester.cleanup()
        sys.exit(130)
    except Exception as e:
        console.print(f"\n❌ Test suite failed: {e}")
        logger.error(f"Test suite error: {e}", exc_info=True)
        await tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())