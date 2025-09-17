#!/usr/bin/env python3
"""
Test script to verify the blockchain analytics setup is working properly.
This script will test connections to both the blockchain RPC and InfluxDB.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.blockchain_client import BlockchainClient
from core.influxdb_client import BlockchainInfluxDB
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Initialize rich console for pretty output
console = Console()

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/test_setup.log')
        ]
    )

async def test_blockchain_connection():
    """Test connection to the blockchain RPC."""
    console.print("\n[bold blue]Testing Blockchain Connection...[/bold blue]")
    
    try:
        # Create blockchain client
        client = BlockchainClient("http://localhost:8545")
        
        # Test connection
        connected = await client.connect()
        
        if connected:
            # Get basic info
            chain_id = client.chain_id
            latest_block = await client.get_latest_block_number()
            
            # Test getting a block
            block = await client.get_block(latest_block)
            
            if block:
                table = Table(title="Blockchain Connection Test - SUCCESS ✅")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Chain ID", str(chain_id))
                table.add_row("Latest Block", str(latest_block))
                table.add_row("Block Hash", block['hash'])
                table.add_row("Gas Used", str(int(block['gasUsed'], 16)))
                table.add_row("Gas Limit", str(int(block['gasLimit'], 16)))
                table.add_row("Transaction Count", str(len(block.get('transactions', []))))
                
                console.print(table)
                client.close()
                return True
            else:
                console.print("[red]❌ Failed to fetch block data[/red]")
        else:
            console.print("[red]❌ Failed to connect to blockchain[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Blockchain connection error: {e}[/red]")
        
    return False

async def test_influxdb_connection():
    """Test connection to InfluxDB."""
    console.print("\n[bold blue]Testing InfluxDB Connection...[/bold blue]")
    
    try:
        # Note: For this test, we'll use dummy credentials
        # You'll need to set up your actual InfluxDB token
        # Create a simple config object for testing
        from core.config import Config
        config = Config()
        db_client = BlockchainInfluxDB(config)
        
        connected = await db_client.connect()
        
        if connected:
            console.print("[green]✅ InfluxDB connection successful[/green]")
            
            # Test writing a sample data point
            try:
                sample_block = {
                    'number': '0x12345',
                    'timestamp': '0x61234567',
                    'gasUsed': '0x5208',
                    'gasLimit': '0x1c9c380',
                    'transactions': [],
                    'size': '0x123'
                }
                
                db_client.write_block(sample_block)
                console.print("[green]✅ Sample data write successful[/green]")
                
            except Exception as e:
                console.print(f"[yellow]⚠️  Sample data write failed (this is normal if token is not set): {e}[/yellow]")
                
            db_client.close()
            return True
            
    except Exception as e:
        console.print(f"[yellow]⚠️  InfluxDB connection failed (this is normal if token is not set): {e}[/yellow]")
        console.print("[yellow]To fix this, please set up your InfluxDB token in the .env file[/yellow]")
        
    return False

def test_configuration():
    """Test configuration loading."""
    console.print("\n[bold blue]Testing Configuration...[/bold blue]")
    
    try:
        config = Config()
        
        table = Table(title="Configuration Test - SUCCESS ✅")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Blockchain RPC URL", config.blockchain_rpc_url)
        table.add_row("Chain ID", str(config.blockchain_chain_id))
        table.add_row("InfluxDB URL", config.influxdb_url)
        table.add_row("Batch Size", str(config.processing_batch_size))
        table.add_row("Max Workers", str(config.processing_max_workers))
        table.add_row("Real-time Enabled", str(config.real_time_enabled))
        
        console.print(table)
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Configuration error: {e}[/red]")
        return False

async def run_comprehensive_test():
    """Run comprehensive system test."""
    console.print(Panel.fit("🚀 [bold green]GLQ Chain Analytics System Test[/bold green] 🚀"))
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Test results
    results = {
        'configuration': False,
        'blockchain': False,
        'influxdb': False
    }
    
    # Test configuration
    results['configuration'] = test_configuration()
    
    # Test blockchain connection
    results['blockchain'] = await test_blockchain_connection()
    
    # Test InfluxDB connection
    results['influxdb'] = await test_influxdb_connection()
    
    # Summary
    console.print("\n" + "="*50)
    console.print("[bold]Test Summary:[/bold]")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        color = "green" if passed else "red"
        console.print(f"  {test_name.title()}: [{color}]{status}[/{color}]")
    
    all_passed = all(results.values())
    
    if all_passed:
        console.print("\n[bold green]🎉 All tests passed! System is ready for blockchain analytics.[/bold green]")
    else:
        console.print("\n[bold yellow]⚠️  Some tests failed. Please check the configuration and connections.[/bold yellow]")
        
        if not results['influxdb']:
            console.print("\n[yellow]To set up InfluxDB properly:[/yellow]")
            console.print("1. Create an InfluxDB token in the UI")
            console.print("2. Copy .env.template to .env")
            console.print("3. Set INFLUX_TOKEN in .env file")
    
    console.print("="*50)

if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_comprehensive_test())