#!/usr/bin/env python3
"""
Quick Sync Progress Checker
Shows current sync progress and estimated completion time
"""

import asyncio
import sys
import warnings
from pathlib import Path
from datetime import datetime, timedelta

# Suppress InfluxDB pivot warning
from influxdb_client.client.warnings import MissingPivotFunction
warnings.simplefilter("ignore", MissingPivotFunction)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.influxdb_client import BlockchainInfluxDB
from core.blockchain_client import BlockchainClient
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

async def check_progress():
    """Check the current sync progress."""
    try:
        # Load configuration
        config = Config()
        
        # Connect to database
        db_client = BlockchainInfluxDB(config)
        await db_client.connect()
        
        # Connect to blockchain to get latest block
        blockchain_client = BlockchainClient(config)
        await blockchain_client.connect()
        
        # Get current progress
        latest_synced = db_client.query_latest_block()
        latest_network = await blockchain_client.get_latest_block_number()
        
        if latest_synced is None:
            latest_synced = 0
            
        # Calculate progress
        total_blocks = latest_network
        progress_pct = (latest_synced / total_blocks) * 100 if total_blocks > 0 else 0
        remaining_blocks = total_blocks - latest_synced
        
        # Create status table
        table = Table(title="🔄 GLQ Chain Sync Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Details", style="yellow")
        
        table.add_row("Latest Synced Block", f"{latest_synced:,}", f"Starting from block 1")
        table.add_row("Latest Network Block", f"{latest_network:,}", f"Chain ID: 614")
        table.add_row("Progress", f"{progress_pct:.2f}%", f"{remaining_blocks:,} blocks remaining")
        
        # Estimate completion time based on current rate
        if latest_synced > 1000:  # Need some data to estimate
            # Assume average rate of 26 blocks/second from sync
            avg_rate = 26
            remaining_seconds = remaining_blocks / avg_rate
            completion_time = datetime.now() + timedelta(seconds=remaining_seconds)
            
            table.add_row("Estimated Rate", f"{avg_rate} blocks/sec", "Based on observed performance")
            table.add_row("Est. Completion", completion_time.strftime("%Y-%m-%d %H:%M:%S"), f"In {remaining_seconds/3600:.1f} hours")
        
        console.print(table)
        
        # Show analytics data if available
        try:
            # Quick query for analytics data
            analytics_query = f'''
            from(bucket: "{config.influxdb_bucket}")
              |> range(start: -1d)
              |> filter(fn: (r) => r["_measurement"] == "token_transfers" or 
                                  r["_measurement"] == "dex_swaps" or 
                                  r["_measurement"] == "liquidity_events" or 
                                  r["_measurement"] == "defi_events")
              |> group(columns: ["_measurement"])
              |> count()
            '''
            
            analytics_result = db_client.query_api.query_data_frame(org=config.influxdb_org, query=analytics_query)
            
            # Handle case where result might be a list or empty
            has_data = False
            if isinstance(analytics_result, list):
                has_data = len(analytics_result) > 0
            elif hasattr(analytics_result, 'empty'):
                has_data = not analytics_result.empty and len(analytics_result) > 0
            else:
                has_data = analytics_result is not None
            
            if has_data:
                analytics_table = Table(title="📊 Analytics Progress")
                analytics_table.add_column("Event Type", style="cyan")
                analytics_table.add_column("Count", style="green")
                
                # Count by measurement
                for measurement in ['token_transfers', 'dex_swaps', 'liquidity_events', 'defi_events']:
                    count = 0
                    if '_measurement' in analytics_result.columns:
                        measurement_data = analytics_result[analytics_result['_measurement'] == measurement]
                        if not measurement_data.empty and '_value' in measurement_data.columns:
                            count = measurement_data['_value'].sum()
                    
                    display_name = {
                        'token_transfers': '🪙 Token Transfers',
                        'dex_swaps': '🔄 DEX Swaps', 
                        'liquidity_events': '💧 Liquidity Events',
                        'defi_events': '🏦 DeFi Events'
                    }.get(measurement, measurement)
                    
                    analytics_table.add_row(display_name, f"{count:,}")
                
                console.print(analytics_table)
            else:
                console.print("📊 Analytics data not yet available (still processing early blocks)")
                
        except Exception as e:
            console.print(f"ℹ️ Analytics data query failed: {e}")
        
        # Clean up
        blockchain_client.close()
        db_client.close()
        
        return True
        
    except Exception as e:
        console.print(f"❌ Error checking progress: {e}")
        return False

async def main():
    console.print(Panel(
        Text("🔍 GLQ Chain Sync Progress Check", style="bold green"),
        subtitle="Current historical sync status",
        border_style="green"
    ))
    
    success = await check_progress()
    
    if success:
        console.print("\n💡 [bold blue]Tip:[/bold blue] Run this script periodically to monitor progress")
        console.print("💡 [bold blue]Tip:[/bold blue] Use 'python scripts/start_realtime_monitor.py' to monitor current chain activity")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())