#!/usr/bin/env python3
"""
Start Web Dashboard for GLQ Chain Analytics
Runs the web monitoring service in background
"""

import asyncio
import sys
import signal
import logging
from pathlib import Path
import platform

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from processors.monitoring_service import MonitoringService
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Global shutdown event
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    console.print(f"\n⚠️ Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

async def main():
    """Start the web monitoring service."""
    console.print(Panel(
        Text("🌐 Starting GLQ Chain Web Dashboard", style="bold blue"),
        subtitle="Web interface for real-time monitoring",
        border_style="blue"
    ))
    
    # Setup signal handlers for graceful shutdown
    if platform.system() != 'Windows':
        # Unix-like systems
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:
        # Windows
        signal.signal(signal.SIGINT, signal_handler)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config = Config()
    
    # Create monitoring service on port 8001
    service = MonitoringService(config, port=8001)
    
    try:
        console.print("🚀 Starting web service...")
        await service.start_service()
        
        console.print(Panel(
            Text("✅ Web Dashboard Running!", style="bold green"),
            subtitle="Access your dashboard at: http://localhost:8001",
            border_style="green"
        ))
        
        console.print("🎯 [bold cyan]Dashboard Features:[/bold cyan]")
        console.print("   • Real-time blockchain metrics")
        console.print("   • Analytics performance monitoring") 
        console.print("   • Live WebSocket updates")
        console.print("   • Start/Stop/Pause controls")
        console.print("")
        console.print("💡 [bold yellow]Tips:[/bold yellow]")
        console.print("   • Open http://localhost:8001 in your browser")
        console.print("   • Use the controls to start/stop monitoring")
        console.print("   • Analytics data updates automatically")
        console.print("   • Press Ctrl+C here to stop the web service")
        
        # Keep running until shutdown is signaled
        try:
            await shutdown_event.wait()
        except asyncio.CancelledError:
            # This is expected when the task is cancelled during shutdown
            pass
            
    except KeyboardInterrupt:
        console.print("\n⚠️ Shutting down web service...")
    except Exception as e:
        console.print(f"❌ Web service error: {e}")
    finally:
        # Ensure clean shutdown regardless of how we exit
        console.print("🛑 Initiating graceful shutdown...")
        try:
            await service.shutdown()
            console.print("✅ Web service stopped gracefully")
        except Exception as shutdown_error:
            console.print(f"⚠️ Error during shutdown: {shutdown_error}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This is handled in main(), but just in case
        console.print("\n🔴 Application interrupted")
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        console.print("👋 Goodbye!")
