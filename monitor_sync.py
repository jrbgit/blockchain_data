#!/usr/bin/env python3
"""
Sync Performance Monitor
Real-time monitoring of sync performance, system resources, and progress tracking.
"""

import asyncio
import json
import psutil
import time
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB

console = Console()

class SyncMonitor:
    """Monitor sync performance and system resources."""
    
    def __init__(self):
        self.config = Config()
        self.db_client = None
        self.checkpoint_file = "sync_checkpoint.json"
        
        # Performance tracking
        self.start_time = None
        self.last_update = None
        self.performance_history = []
        
    async def initialize(self):
        """Initialize database connection."""
        try:
            if self.config.influxdb_token:
                self.db_client = BlockchainInfluxDB(self.config)
                await self.db_client.connect()
                return True
        except Exception as e:
            console.print(f"Warning: Could not connect to database: {e}")
        return False
    
    def load_checkpoint(self):
        """Load current sync progress."""
        try:
            if Path(self.checkpoint_file).exists():
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    async def get_blockchain_latest_block(self):
        """Get latest block from blockchain."""
        try:
            from core.blockchain_client import BlockchainClient
            client = BlockchainClient(self.config)
            await client.connect()
            latest = await client.get_latest_block_number()
            client.close()
            return latest
        except Exception:
            return None
    
    def get_system_stats(self):
        """Get current system resource usage."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=None),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used_gb': psutil.virtual_memory().used / (1024**3),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'disk_io': psutil.disk_io_counters(),
            'network_io': psutil.net_io_counters()
        }
    
    def calculate_eta(self, current_block, target_block, blocks_per_second):
        """Calculate estimated time to completion."""
        if blocks_per_second <= 0:
            return "Unknown"
        
        remaining_blocks = target_block - current_block
        seconds_remaining = remaining_blocks / blocks_per_second
        
        eta = datetime.now() + timedelta(seconds=seconds_remaining)
        return eta.strftime("%H:%M:%S")
    
    def create_dashboard(self, stats):
        """Create the monitoring dashboard."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=5)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Header
        header_text = Text("⚡ GLQ Chain Sync Performance Monitor", style="bold white")
        layout["header"].update(Panel(header_text, border_style="white"))
        
        # Sync Progress Table
        progress_table = Table(title="📊 Sync Progress", show_header=True)
        progress_table.add_column("Metric", style="cyan")
        progress_table.add_column("Value", style="green")
        progress_table.add_column("Details", style="yellow")
        
        checkpoint = stats.get('checkpoint', {})
        current_block = checkpoint.get('last_synced_block', 0)
        target_block = stats.get('target_block', 0)
        blocks_per_second = checkpoint.get('avg_blocks_per_second', 0)
        
        progress_percent = (current_block / max(target_block, 1)) * 100 if target_block > 0 else 0
        remaining_blocks = max(0, target_block - current_block)
        
        progress_table.add_row("Current Block", f"{current_block:,}", f"{progress_percent:.2f}% complete")
        progress_table.add_row("Target Block", f"{target_block:,}", f"{remaining_blocks:,} remaining")
        progress_table.add_row("Sync Rate", f"{blocks_per_second:.2f}/sec", "Current average")
        
        if blocks_per_second > 0:
            eta_time = self.calculate_eta(current_block, target_block, blocks_per_second)
            hours_remaining = remaining_blocks / blocks_per_second / 3600
            progress_table.add_row("ETA", eta_time, f"~{hours_remaining:.1f} hours")
        
        layout["left"].update(Panel(progress_table, border_style="green"))
        
        # System Resources Table
        system_table = Table(title="💻 System Resources", show_header=True)
        system_table.add_column("Resource", style="cyan")
        system_table.add_column("Usage", style="green")
        system_table.add_column("Status", style="yellow")
        
        sys_stats = stats.get('system', {})
        
        cpu_percent = sys_stats.get('cpu_percent', 0)
        cpu_status = "🟢 Good" if cpu_percent < 80 else "🟡 High" if cpu_percent < 95 else "🔴 Critical"
        system_table.add_row("CPU", f"{cpu_percent:.1f}%", cpu_status)
        
        memory_percent = sys_stats.get('memory_percent', 0)
        memory_used = sys_stats.get('memory_used_gb', 0)
        memory_total = sys_stats.get('memory_total_gb', 0)
        memory_status = "🟢 Good" if memory_percent < 80 else "🟡 High" if memory_percent < 95 else "🔴 Critical"
        system_table.add_row("Memory", f"{memory_percent:.1f}%", f"{memory_used:.1f}GB / {memory_total:.1f}GB")
        
        # Network I/O
        if 'network_io' in sys_stats and sys_stats['network_io']:
            net_io = sys_stats['network_io']
            bytes_sent_mb = net_io.bytes_sent / (1024**2)
            bytes_recv_mb = net_io.bytes_recv / (1024**2)
            system_table.add_row("Network", f"↑{bytes_sent_mb:.1f}MB ↓{bytes_recv_mb:.1f}MB", "Total session")
        
        layout["right"].update(Panel(system_table, border_style="blue"))
        
        # Performance History (Footer)
        if len(self.performance_history) > 1:
            perf_table = Table(title="📈 Performance History (Last 10 measurements)")
            perf_table.add_column("Time", style="cyan")
            perf_table.add_column("Block", style="green")
            perf_table.add_column("Rate (blocks/sec)", style="yellow")
            perf_table.add_column("CPU %", style="red")
            perf_table.add_column("Memory %", style="blue")
            
            # Show last 10 measurements
            recent_history = self.performance_history[-10:]
            for entry in recent_history:
                perf_table.add_row(
                    entry['time'].strftime("%H:%M:%S"),
                    f"{entry['block']:,}",
                    f"{entry['rate']:.2f}",
                    f"{entry['cpu']:.1f}",
                    f"{entry['memory']:.1f}"
                )
            
            layout["footer"].update(Panel(perf_table, border_style="magenta"))
        else:
            layout["footer"].update(Panel("Collecting performance data...", border_style="magenta"))
        
        return layout
    
    async def monitor(self, update_interval=5):
        """Run the monitoring loop."""
        await self.initialize()
        
        console.print("🚀 Starting sync performance monitor...")
        console.print("Press Ctrl+C to exit")
        
        self.start_time = datetime.now()
        
        with Live(console=console, refresh_per_second=1) as live:
            try:
                while True:
                    # Collect data
                    checkpoint = self.load_checkpoint()
                    system_stats = self.get_system_stats()
                    target_block = await self.get_blockchain_latest_block()
                    
                    # Update performance history
                    if checkpoint:
                        current_time = datetime.now()
                        self.performance_history.append({
                            'time': current_time,
                            'block': checkpoint.get('last_synced_block', 0),
                            'rate': checkpoint.get('avg_blocks_per_second', 0),
                            'cpu': system_stats['cpu_percent'],
                            'memory': system_stats['memory_percent']
                        })
                        
                        # Keep only last 50 entries
                        if len(self.performance_history) > 50:
                            self.performance_history = self.performance_history[-50:]
                    
                    # Prepare stats for dashboard
                    stats = {
                        'checkpoint': checkpoint or {},
                        'system': system_stats,
                        'target_block': target_block or 0,
                        'monitor_uptime': datetime.now() - self.start_time
                    }
                    
                    # Update dashboard
                    dashboard = self.create_dashboard(stats)
                    live.update(dashboard)
                    
                    # Wait for next update
                    await asyncio.sleep(update_interval)
                    
            except KeyboardInterrupt:
                console.print("\n👋 Monitor stopped by user")

async def main():
    """Main function."""
    monitor = SyncMonitor()
    
    # Check if sync is running
    if not Path("sync_checkpoint.json").exists():
        console.print("⚠️  No sync checkpoint found. Make sure fast_sync.py is running.")
        console.print("   Run: python fast_sync.py")
        return
    
    await monitor.monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        sys.exit(0)