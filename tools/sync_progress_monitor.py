#!/usr/bin/env python3
"""
Advanced Sync Progress Monitor
Comprehensive real-time monitoring of full blockchain sync progress after reset_and_sync.py execution.

Features:
- Real-time progress tracking with ETA calculations
- Performance metrics and system resource monitoring  
- Analytics processing progress
- Historical performance graphs
- Automatic detection of sync completion
- Health monitoring and alerts
"""

import asyncio
import json
import psutil
import time
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.align import Align
import sys
import os

# Suppress InfluxDB warnings
from influxdb_client.client.warnings import MissingPivotFunction
warnings.simplefilter("ignore", MissingPivotFunction)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / \"src\"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB
from core.blockchain_client import BlockchainClient

console = Console()

class AdvancedSyncMonitor:
    """Advanced sync progress monitor with comprehensive tracking."""
    
    def __init__(self, refresh_interval=3):
        self.config = Config()
        self.db_client = None
        self.blockchain_client = None
        self.refresh_interval = refresh_interval
        
        # Tracking data
        self.start_time = datetime.now()
        self.last_block_check = 0
        self.last_check_time = datetime.now()
        self.performance_history = deque(maxlen=100)  # Last 100 measurements
        self.rate_history = deque(maxlen=20)  # Last 20 rate measurements for smoothing
        
        # Analytics tracking
        self.analytics_counts = {
            'blocks': 0,
            'transactions': 0, 
            'token_transfers': 0,
            'dex_swaps': 0,
            'liquidity_events': 0,
            'defi_events': 0,
            'contract_deployments': 0
        }
        
        # System health
        self.health_alerts = []
        self.max_alerts = 10
        
        # Progress state
        self.is_sync_complete = False
        self.completion_time = None
        
    async def initialize(self):
        """Initialize database and blockchain connections."""
        console.print("🔧 Initializing connections...")
        
        try:
            # Initialize database client
            if self.config.influxdb_token:
                self.db_client = BlockchainInfluxDB(self.config)
                db_connected = await self.db_client.connect()
                if not db_connected:
                    console.print("❌ Failed to connect to InfluxDB")
                    return False
                console.print("✅ Connected to InfluxDB")
            else:
                console.print("❌ No InfluxDB token configured")
                return False
            
            # Initialize blockchain client
            self.blockchain_client = BlockchainClient(self.config)
            blockchain_connected = await self.blockchain_client.connect()
            if not blockchain_connected:
                console.print("❌ Failed to connect to blockchain")
                return False
            console.print("✅ Connected to GLQ Chain")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Initialization failed: {e}")
            return False
    
    async def get_sync_progress(self):
        """Get current sync progress from database."""
        try:
            if not self.db_client:
                return None
                
            # Get latest synced block
            latest_synced = self.db_client.query_latest_block()
            if latest_synced is None:
                latest_synced = 0
                
            # Get network latest block
            network_latest = await self.blockchain_client.get_latest_block_number()
            
            # Calculate progress metrics
            total_blocks = network_latest
            progress_pct = (latest_synced / total_blocks) * 100 if total_blocks > 0 else 0
            remaining_blocks = total_blocks - latest_synced
            
            return {
                'latest_synced': latest_synced,
                'network_latest': network_latest,
                'total_blocks': total_blocks,
                'progress_pct': progress_pct,
                'remaining_blocks': remaining_blocks
            }
            
        except Exception as e:
            console.print(f"Error getting sync progress: {e}")
            return None
    
    async def get_analytics_progress(self):
        """Get analytics processing progress."""
        try:
            if not self.db_client:
                return self.analytics_counts
            
            # Query different measurement types
            measurements = [
                'blocks', 'transactions', 'token_transfers', 'dex_swaps', 
                'liquidity_events', 'defi_events', 'contract_deployments'
            ]
            
            analytics_data = {}
            
            for measurement in measurements:
                try:
                    # Count records in each measurement
                    query = f'''
                    from(bucket: "{self.config.influxdb_bucket}")
                      |> range(start: 1970-01-01T00:00:00Z)
                      |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                      |> count()
                    '''
                    
                    result = self.db_client.query_api.query_data_frame(
                        org=self.config.influxdb_org, 
                        query=query
                    )
                    
                    count = 0
                    if hasattr(result, 'empty') and not result.empty:
                        if '_value' in result.columns:
                            count = result['_value'].sum() if len(result) > 0 else 0
                    elif isinstance(result, list) and len(result) > 0:
                        count = sum(df['_value'].sum() if '_value' in df.columns else 0 for df in result)
                    
                    analytics_data[measurement] = count
                    
                except Exception:
                    analytics_data[measurement] = 0
            
            self.analytics_counts = analytics_data
            return analytics_data
            
        except Exception as e:
            console.print(f"Error getting analytics progress: {e}")
            return self.analytics_counts
    
    def calculate_sync_rate(self, current_block):
        """Calculate current sync rate in blocks per second."""
        current_time = datetime.now()
        
        if self.last_block_check > 0:
            time_diff = (current_time - self.last_check_time).total_seconds()
            block_diff = current_block - self.last_block_check
            
            if time_diff > 0:
                rate = block_diff / time_diff
                self.rate_history.append(rate)
                
                # Return smoothed rate (average of last measurements)
                return sum(self.rate_history) / len(self.rate_history)
        
        self.last_block_check = current_block
        self.last_check_time = current_time
        return 0.0
    
    def calculate_eta(self, remaining_blocks, blocks_per_second):
        """Calculate estimated time to completion."""
        if blocks_per_second <= 0:
            return "Unknown", 0
        
        seconds_remaining = remaining_blocks / blocks_per_second
        eta_time = datetime.now() + timedelta(seconds=seconds_remaining)
        
        return eta_time.strftime("%Y-%m-%d %H:%M:%S"), seconds_remaining
    
    def get_system_health(self):
        """Get system resource usage and health status."""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            # Use current drive for Windows compatibility
            disk_path = os.getcwd()[:3] if os.name == 'nt' else '/'
            disk = psutil.disk_usage(disk_path)
            
            # Check for performance issues
            alerts = []
            
            if cpu_percent > 90:
                alerts.append("🔴 CPU usage critical (>90%)")
            elif cpu_percent > 80:
                alerts.append("🟡 CPU usage high (>80%)")
            
            if memory.percent > 90:
                alerts.append("🔴 Memory usage critical (>90%)")
            elif memory.percent > 80:
                alerts.append("🟡 Memory usage high (>80%)")
            
            if disk.percent > 90:
                alerts.append("🔴 Disk usage critical (>90%)")
            elif disk.percent > 85:
                alerts.append("🟡 Disk usage high (>85%)")
            
            # Add new alerts to history
            for alert in alerts:
                if alert not in self.health_alerts:
                    self.health_alerts.append(f"{datetime.now().strftime('%H:%M:%S')} - {alert}")
            
            # Keep only recent alerts
            if len(self.health_alerts) > self.max_alerts:
                self.health_alerts = self.health_alerts[-self.max_alerts:]
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_total_gb': memory.total / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'alerts': alerts,
                'alert_history': self.health_alerts
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def create_progress_panel(self, sync_data, analytics_data, system_health, blocks_per_second):
        """Create the main progress panel."""
        if not sync_data:
            return Panel("❌ Unable to retrieve sync data", border_style="red")
        
        # Progress bar
        progress_text = Text()
        progress_text.append(f"Block Progress: ", style="cyan")
        progress_text.append(f"{sync_data['latest_synced']:,} / {sync_data['total_blocks']:,}", style="green")
        progress_text.append(f" ({sync_data['progress_pct']:.2f}%)", style="yellow")
        
        # Rate and ETA
        eta_str, eta_seconds = self.calculate_eta(sync_data['remaining_blocks'], blocks_per_second)
        
        rate_text = Text()
        rate_text.append(f"Sync Rate: ", style="cyan")
        rate_text.append(f"{blocks_per_second:.2f} blocks/sec", style="green")
        
        eta_text = Text()
        eta_text.append(f"ETA: ", style="cyan")
        if eta_seconds > 0:
            eta_text.append(f"{eta_str}", style="green")
            eta_text.append(f" (~{eta_seconds/3600:.1f} hours)", style="yellow")
        else:
            eta_text.append("Calculating...", style="yellow")
        
        # Combine all text
        content = Text()
        content.append(progress_text)
        content.append("\n")
        content.append(rate_text)
        content.append("\n")
        content.append(eta_text)
        
        # Check if sync is complete
        if sync_data['progress_pct'] >= 99.9 and not self.is_sync_complete:
            self.is_sync_complete = True
            self.completion_time = datetime.now()
            content.append("\n")
            content.append("🎉 SYNC COMPLETE! 🎉", style="bold green")
        
        return Panel(content, title="📊 Sync Progress", border_style="green")
    
    def create_analytics_panel(self, analytics_data):
        """Create analytics progress panel."""
        table = Table(show_header=True, header_style="cyan")
        table.add_column("Data Type", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Status", style="yellow")
        
        # Analytics data with icons and status
        analytics_info = {
            'blocks': ('📦', 'Core'),
            'transactions': ('💸', 'Core'),
            'token_transfers': ('🪙', 'Token Analytics'),
            'dex_swaps': ('🔄', 'DEX Analytics'),
            'liquidity_events': ('💧', 'DeFi Analytics'),
            'defi_events': ('🏦', 'DeFi Analytics'),
            'contract_deployments': ('📜', 'Contract Analytics')
        }
        
        for measurement, count in analytics_data.items():
            icon, category = analytics_info.get(measurement, ('📊', 'Unknown'))
            status = "✅ Active" if count > 0 else "⏳ Pending"
            table.add_row(f"{icon} {measurement.replace('_', ' ').title()}", f"{count:,}", status)
        
        return Panel(table, title="🔬 Analytics Progress", border_style="blue")
    
    def create_system_panel(self, system_health):
        """Create system health panel."""
        if 'error' in system_health:
            return Panel(f"❌ System monitoring error: {system_health['error']}", border_style="red")
        
        table = Table(show_header=True, header_style="cyan")
        table.add_column("Resource", style="cyan")
        table.add_column("Usage", style="green", justify="right") 
        table.add_column("Status", style="yellow")
        
        # CPU status
        cpu_status = "🟢 Good" if system_health['cpu_percent'] < 70 else "🟡 High" if system_health['cpu_percent'] < 90 else "🔴 Critical"
        table.add_row("CPU", f"{system_health['cpu_percent']:.1f}%", cpu_status)
        
        # Memory status  
        memory_status = "🟢 Good" if system_health['memory_percent'] < 70 else "🟡 High" if system_health['memory_percent'] < 90 else "🔴 Critical"
        table.add_row("Memory", f"{system_health['memory_percent']:.1f}%", f"{system_health['memory_used_gb']:.1f}GB / {system_health['memory_total_gb']:.1f}GB")
        
        # Disk status
        disk_status = "🟢 Good" if system_health['disk_percent'] < 80 else "🟡 High" if system_health['disk_percent'] < 90 else "🔴 Critical"
        table.add_row("Disk", f"{system_health['disk_percent']:.1f}%", f"{system_health['disk_free_gb']:.1f}GB free")
        
        # Current alerts
        if system_health.get('alerts'):
            alert_text = "\n".join(system_health['alerts'])
            table.add_row("Alerts", f"{len(system_health['alerts'])} active", "⚠️  Check system")
        
        return Panel(table, title="💻 System Health", border_style="red" if system_health.get('alerts') else "blue")
    
    def create_performance_history_panel(self):
        """Create performance history panel."""
        if len(self.performance_history) < 2:
            return Panel("Collecting performance data...", title="📈 Performance History", border_style="magenta")
        
        table = Table(show_header=True, header_style="cyan")
        table.add_column("Time", style="cyan", width=8)
        table.add_column("Block", style="green", justify="right", width=12)
        table.add_column("Rate/sec", style="yellow", justify="right", width=8)
        table.add_column("CPU%", style="red", justify="right", width=6)
        table.add_column("Mem%", style="blue", justify="right", width=6)
        
        # Show last 8 measurements
        recent_history = list(self.performance_history)[-8:]
        for entry in recent_history:
            table.add_row(
                entry['time'].strftime("%H:%M:%S"),
                f"{entry['block']:,}",
                f"{entry['rate']:.1f}",
                f"{entry['cpu']:.0f}",
                f"{entry['memory']:.0f}"
            )
        
        return Panel(table, title="📈 Performance History", border_style="magenta")
    
    def create_dashboard(self, sync_data, analytics_data, system_health, blocks_per_second):
        """Create the complete monitoring dashboard."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=12)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="progress"),
            Layout(name="analytics")
        )
        
        layout["right"].split_column(
            Layout(name="system"),
            Layout(name="history")
        )
        
        # Header
        uptime = datetime.now() - self.start_time
        header_text = Text(f"⚡ GLQ Chain Full Sync Monitor - Running for {uptime}", style="bold white")
        if self.is_sync_complete:
            header_text.append(" - 🎉 SYNC COMPLETE!", style="bold green")
        layout["header"].update(Panel(header_text, border_style="white"))
        
        # Main panels
        layout["progress"].update(self.create_progress_panel(sync_data, analytics_data, system_health, blocks_per_second))
        layout["analytics"].update(self.create_analytics_panel(analytics_data))
        layout["system"].update(self.create_system_panel(system_health))
        layout["history"].update(self.create_performance_history_panel())
        
        # Footer with instructions
        footer_text = Text()
        footer_text.append("💡 Press Ctrl+C to exit monitor", style="yellow")
        footer_text.append(" • ", style="white")
        footer_text.append("Monitor will continue until sync is complete", style="cyan")
        if self.is_sync_complete and self.completion_time:
            footer_text.append(f"\n🎉 Sync completed at {self.completion_time.strftime('%Y-%m-%d %H:%M:%S')}", style="bold green")
        
        layout["footer"].update(Panel(footer_text, border_style="yellow"))
        
        return layout
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        console.print("🚀 Starting advanced sync progress monitor...")
        console.print("Press Ctrl+C to exit\n")
        
        with Live(console=console, refresh_per_second=1/self.refresh_interval) as live:
            try:
                while True:
                    # Collect all monitoring data
                    sync_data = await self.get_sync_progress()
                    analytics_data = await self.get_analytics_progress()
                    system_health = self.get_system_health()
                    
                    # Calculate sync rate
                    blocks_per_second = 0.0
                    if sync_data:
                        blocks_per_second = self.calculate_sync_rate(sync_data['latest_synced'])
                    
                    # Store performance data
                    current_time = datetime.now()
                    self.performance_history.append({
                        'time': current_time,
                        'block': sync_data['latest_synced'] if sync_data else 0,
                        'rate': blocks_per_second,
                        'cpu': system_health.get('cpu_percent', 0),
                        'memory': system_health.get('memory_percent', 0)
                    })
                    
                    # Update dashboard
                    dashboard = self.create_dashboard(sync_data, analytics_data, system_health, blocks_per_second)
                    live.update(dashboard)
                    
                    # Check if sync is complete and user wants to exit
                    if self.is_sync_complete:
                        # Show completion message for 30 seconds then ask user
                        await asyncio.sleep(30)
                        break
                    
                    # Wait for next refresh
                    await asyncio.sleep(self.refresh_interval)
                    
            except KeyboardInterrupt:
                console.print("\n👋 Monitor stopped by user")
    
    async def cleanup(self):
        """Cleanup connections."""
        if self.blockchain_client:
            self.blockchain_client.close()
        if self.db_client:
            self.db_client.close()

async def main():
    """Main function."""
    console.print(Panel(
        Text("⚡ Advanced GLQ Chain Sync Progress Monitor", style="bold green"),
        subtitle="Real-time monitoring of full blockchain synchronization",
        border_style="green"
    ))
    
    # Check if sync process might be running
    possible_sync_indicators = [
        Path("logs/historical_processing.log"),
        Path("logs/full_sync.log"),
        Path("logs/blockchain_analytics.log")
    ]
    
    sync_might_be_running = any(
        log_file.exists() and 
        (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).total_seconds() < 300
        for log_file in possible_sync_indicators
    )
    
    if not sync_might_be_running:
        console.print("\n⚠️  [yellow]Warning:[/yellow] No recent sync activity detected.")
        console.print("Make sure you've started the sync process with:")
        console.print("  [cyan]python reset_and_sync.py[/cyan]")
        console.print("  [cyan]python glq_analytics.py sync[/cyan]")
        console.print("  [cyan]python src/processors/historical_clean.py[/cyan]")
        
        response = console.input("\nContinue monitoring anyway? [y/N]: ")
        if response.lower() != 'y':
            return
    
    monitor = AdvancedSyncMonitor(refresh_interval=3)
    
    try:
        # Initialize connections
        if not await monitor.initialize():
            console.print("❌ Failed to initialize monitor")
            return
        
        # Start monitoring
        await monitor.monitor_loop()
        
        if monitor.is_sync_complete:
            console.print(Panel(
                Text("🎉 BLOCKCHAIN SYNC COMPLETED SUCCESSFULLY! 🎉", style="bold green"),
                subtitle=f"Completed at {monitor.completion_time.strftime('%Y-%m-%d %H:%M:%S')}",
                border_style="green"
            ))
            
            console.print("\n📊 Next steps:")
            console.print("  • Start real-time monitoring: [cyan]python glq_analytics.py monitor[/cyan]")
            console.print("  • View web dashboard: [cyan]python scripts/start_monitor_service.py[/cyan]")
            console.print("  • Generate reports: [cyan]python start_multichain_monitor.py --mode analytics[/cyan]")
        
    except Exception as e:
        console.print(f"❌ Monitor error: {e}")
    finally:
        await monitor.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        sys.exit(0)
