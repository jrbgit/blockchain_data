#!/usr/bin/env python3
"""
Configuration Optimizer for High-Performance Sync
Updates configuration settings for maximum throughput during initial sync.
"""

import sys
import yaml
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

console = Console()

def optimize_config():
    """Optimize configuration for high-performance sync."""
    
    config_path = Path("config/config.yaml")
    
    if not config_path.exists():
        console.print("❌ Configuration file not found")
        return False
    
    console.print(Panel(
        Text("⚙️ Configuration Optimizer", style="bold cyan"),
        subtitle="Optimizing for maximum sync performance",
        border_style="cyan"
    ))
    
    try:
        # Load current configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        console.print("📄 Current configuration loaded")
        
        # Backup original configuration
        backup_path = config_path.with_suffix('.yaml.backup')
        with open(backup_path, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        console.print(f"💾 Backup saved to: {backup_path}")
        
        # Display current settings
        table = Table(title="🔧 Performance Settings Optimization")
        table.add_column("Setting", style="cyan")
        table.add_column("Current", style="yellow")
        table.add_column("Optimized", style="green")
        table.add_column("Improvement", style="magenta")
        
        # Optimize processing settings
        old_batch_size = config['processing']['batch_size']
        new_batch_size = 2000
        config['processing']['batch_size'] = new_batch_size
        table.add_row("Batch Size", f"{old_batch_size:,}", f"{new_batch_size:,}", f"{new_batch_size/old_batch_size:.1f}x")
        
        old_max_workers = config['processing']['max_workers']
        new_max_workers = 16
        config['processing']['max_workers'] = new_max_workers  
        table.add_row("Max Workers", str(old_max_workers), str(new_max_workers), f"{new_max_workers/old_max_workers:.1f}x")
        
        # Optimize performance settings
        old_max_conn = config['performance']['max_connections']
        new_max_conn = 50
        config['performance']['max_connections'] = new_max_conn
        table.add_row("Max Connections", str(old_max_conn), str(new_max_conn), f"{new_max_conn/old_max_conn:.1f}x")
        
        old_timeout = config['performance']['connection_timeout']
        new_timeout = 60
        config['performance']['connection_timeout'] = new_timeout
        table.add_row("Connection Timeout", f"{old_timeout}s", f"{new_timeout}s", f"{new_timeout/old_timeout:.1f}x")
        
        # Disable analytics for faster sync
        old_analytics = config['analytics']['enabled']
        config['analytics']['enabled'] = False
        config['analytics']['realtime']['enabled'] = False
        table.add_row("Analytics", "Enabled" if old_analytics else "Disabled", "Disabled", "Skip overhead")
        
        # Optimize data extraction
        config['processing']['extract_transaction_traces'] = False
        config['processing']['extract_internal_transactions'] = False
        config['processing']['extract_logs'] = False
        config['processing']['extract_contract_code'] = False
        table.add_row("Data Extraction", "Full", "Basic", "Skip expensive ops")
        
        # Add memory optimization
        config['performance']['max_memory_usage'] = "8GB"
        config['performance']['gc_threshold'] = 100000
        
        console.print(table)
        
        # Save optimized configuration
        with open(config_path, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        
        console.print("✅ Configuration optimized for high-performance sync!")
        
        # Display recommendations
        console.print(Panel(
            Text("📋 Additional Recommendations", style="bold yellow"),
            border_style="yellow"
        ))
        
        recommendations = [
            "🔧 Use fast_sync.py instead of reset_and_sync.py for initial sync",
            "💾 Ensure SSD storage for InfluxDB data directory",
            "🌐 Run GLQ node locally to minimize network latency",
            "🔋 Consider running sync during off-peak hours",
            "📊 Monitor system resources (CPU, memory, disk I/O)",
            "⚡ After initial sync, re-enable analytics with config restore"
        ]
        
        for rec in recommendations:
            console.print(f"  {rec}")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Configuration optimization failed: {e}")
        return False

def restore_config():
    """Restore original configuration from backup."""
    
    config_path = Path("config/config.yaml")
    backup_path = config_path.with_suffix('.yaml.backup')
    
    if not backup_path.exists():
        console.print("❌ No backup configuration found")
        return False
    
    try:
        # Restore from backup
        with open(backup_path, 'r') as f:
            config = yaml.safe_load(f)
        
        with open(config_path, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        
        console.print("✅ Configuration restored from backup")
        return True
        
    except Exception as e:
        console.print(f"❌ Configuration restore failed: {e}")
        return False

def main():
    """Main function."""
    console.print(Panel(
        Text("⚡ GLQ Chain Configuration Optimizer", style="bold white"),
        subtitle="Maximize sync performance",
        border_style="white"
    ))
    
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        return restore_config()
    else:
        return optimize_config()

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        sys.exit(0)
