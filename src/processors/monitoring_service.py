"""
Blockchain Monitoring Service
Provides a web API for monitoring and controlling the real-time blockchain monitor.
"""

import asyncio
import logging
import json
import signal
import sys
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from aiohttp import web, WSMsgType
import aiohttp_cors


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.realtime_monitor import RealtimeMonitor
from core.config import Config

logger = logging.getLogger(__name__)


class MonitoringService:
    """Web service for monitoring blockchain analytics."""
    
    def __init__(self, config: Config, port: int = 8000):
        self.config = config
        self.port = port
        self.app = web.Application()
        self.monitor: Optional[RealtimeMonitor] = None
        self.websocket_connections = set()
        
        # Setup routes
        self._setup_routes()
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
            
    def _setup_routes(self):
        """Setup API routes."""
        # API endpoints
        self.app.router.add_get('/api/status', self.get_status)
        self.app.router.add_get('/api/statistics', self.get_statistics)
        self.app.router.add_post('/api/start', self.start_monitor)
        self.app.router.add_post('/api/stop', self.stop_monitor)
        self.app.router.add_post('/api/pause', self.pause_monitor)
        self.app.router.add_post('/api/resume', self.resume_monitor)
        
        # WebSocket for live updates
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # Static files (dashboard)
        self.app.router.add_get('/', self.dashboard)
        self.app.router.add_get('/dashboard', self.dashboard)
        
        # Health check
        self.app.router.add_get('/health', self.health_check)
        
    async def get_status(self, request: web.Request) -> web.Response:
        """Get current monitoring status."""
        try:
            if self.monitor:
                status = self.monitor.get_status()
                status['service_status'] = 'running'
            else:
                status = {
                    'service_status': 'not_initialized',
                    'running': False,
                    'paused': False,
                    'last_processed_block': 0,
                    'latest_network_block': 0,
                    'processing_lag': 0,
                    'statistics': {},
                    'uptime': 0
                }
                
            return web.json_response(status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def get_statistics(self, request: web.Request) -> web.Response:
        """Get detailed statistics."""
        try:
            if not self.monitor:
                return web.json_response({'error': 'Monitor not initialized'}, status=400)
                
            stats = self.monitor.get_status()
            
            # Add additional computed metrics
            if stats['statistics'].get('uptime', 0) > 0:
                uptime_hours = stats['statistics']['uptime'] / 3600
                stats['computed_metrics'] = {
                    'uptime_hours': round(uptime_hours, 2),
                    'blocks_per_hour': round(stats['statistics']['blocks_processed'] / max(uptime_hours, 0.01), 2),
                    'transactions_per_hour': round(stats['statistics']['transactions_processed'] / max(uptime_hours, 0.01), 2),
                    'error_rate': round(stats['statistics']['errors'] / max(stats['statistics']['blocks_processed'], 1) * 100, 4),
                    'efficiency': round((stats['statistics']['blocks_processed'] / 
                                       max(stats['statistics']['blocks_processed'] + stats['statistics']['errors'], 1)) * 100, 2)
                }
            else:
                stats['computed_metrics'] = {}
                
            return web.json_response(stats)
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def start_monitor(self, request: web.Request) -> web.Response:
        """Start the blockchain monitor."""
        try:
            if self.monitor and self.monitor.running:
                return web.json_response({'error': 'Monitor is already running'}, status=400)
                
            # Create new monitor if needed
            if not self.monitor:
                self.monitor = RealtimeMonitor(self.config)
                
            # Start monitoring in background task
            asyncio.create_task(self._run_monitor())
            
            return web.json_response({'success': True, 'message': 'Monitor starting...'})
        except Exception as e:
            logger.error(f"Error starting monitor: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def stop_monitor(self, request: web.Request) -> web.Response:
        """Stop the blockchain monitor."""
        try:
            if not self.monitor or not self.monitor.running:
                return web.json_response({'error': 'Monitor is not running'}, status=400)
                
            await self.monitor.stop_monitoring()
            return web.json_response({'success': True, 'message': 'Monitor stopped'})
        except Exception as e:
            logger.error(f"Error stopping monitor: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def pause_monitor(self, request: web.Request) -> web.Response:
        """Pause the blockchain monitor."""
        try:
            if not self.monitor or not self.monitor.running:
                return web.json_response({'error': 'Monitor is not running'}, status=400)
                
            self.monitor.pause_monitoring()
            return web.json_response({'success': True, 'message': 'Monitor paused'})
        except Exception as e:
            logger.error(f"Error pausing monitor: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def resume_monitor(self, request: web.Request) -> web.Response:
        """Resume the blockchain monitor."""
        try:
            if not self.monitor or not self.monitor.running:
                return web.json_response({'error': 'Monitor is not running'}, status=400)
                
            self.monitor.resume_monitoring()
            return web.json_response({'success': True, 'message': 'Monitor resumed'})
        except Exception as e:
            logger.error(f"Error resuming monitor: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for live updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        logger.info(f"WebSocket connection established (total: {len(self.websocket_connections)})")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        # Handle WebSocket commands if needed
                        if data.get('command') == 'get_status':
                            status = await self._get_status_data()
                            await ws.send_str(json.dumps({'type': 'status', 'data': status}, cls=DateTimeEncoder))
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({'type': 'error', 'message': 'Invalid JSON'}))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.websocket_connections.discard(ws)
            logger.info(f"WebSocket connection closed (remaining: {len(self.websocket_connections)})")
            
        return ws
        
    async def dashboard(self, request: web.Request) -> web.Response:
        """Serve the dashboard HTML."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GLQ Chain Analytics - Real-time Monitor</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin: 0;
            background: linear-gradient(45deg, #00d4ff, #5b86e5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .status-card h3 {
            margin: 0 0 15px 0;
            color: #00d4ff;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .metric:last-child {
            border-bottom: none;
        }
        .metric-value {
            font-weight: bold;
            color: #5b86e5;
        }
        .controls {
            text-align: center;
            margin: 30px 0;
        }
        .btn {
            background: linear-gradient(45deg, #00d4ff, #5b86e5);
            border: none;
            color: white;
            padding: 12px 24px;
            margin: 0 10px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 212, 255, 0.3);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background: #00ff88; }
        .status-paused { background: #ffaa00; }
        .status-stopped { background: #ff4444; }
        .log {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            height: 200px;
            overflow-y: auto;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 GLQ Chain Analytics</h1>
            <p>Real-time Blockchain Monitoring Dashboard</p>
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>📊 System Status</h3>
                <div class="metric">
                    <span>Status:</span>
                    <span id="status-indicator">🔴 Loading...</span>
                </div>
                <div class="metric">
                    <span>Uptime:</span>
                    <span class="metric-value" id="uptime">--</span>
                </div>
                <div class="metric">
                    <span>Chain ID:</span>
                    <span class="metric-value">614</span>
                </div>
                <div class="metric">
                    <span>Last Update:</span>
                    <span class="metric-value" id="last-update">--</span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>⛓️ Block Information</h3>
                <div class="metric">
                    <span>Latest Network Block:</span>
                    <span class="metric-value" id="latest-block">--</span>
                </div>
                <div class="metric">
                    <span>Last Processed Block:</span>
                    <span class="metric-value" id="processed-block">--</span>
                </div>
                <div class="metric">
                    <span>Processing Lag:</span>
                    <span class="metric-value" id="processing-lag">--</span>
                </div>
                <div class="metric">
                    <span>Processing Rate:</span>
                    <span class="metric-value" id="processing-rate">--</span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>📈 Statistics</h3>
                <div class="metric">
                    <span>Blocks Processed:</span>
                    <span class="metric-value" id="blocks-processed">--</span>
                </div>
                <div class="metric">
                    <span>Transactions:</span>
                    <span class="metric-value" id="transactions">--</span>
                </div>
                <div class="metric">
                    <span>Events:</span>
                    <span class="metric-value" id="events">--</span>
                </div>
                <div class="metric">
                    <span>Errors:</span>
                    <span class="metric-value" id="errors">--</span>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn" id="start-btn" onclick="startMonitor()">▶️ Start</button>
            <button class="btn" id="pause-btn" onclick="pauseMonitor()">⏸️ Pause</button>
            <button class="btn" id="resume-btn" onclick="resumeMonitor()">▶️ Resume</button>
            <button class="btn" id="stop-btn" onclick="stopMonitor()">⏹️ Stop</button>
        </div>
        
        <div class="status-card">
            <h3>📋 Activity Log</h3>
            <div id="activity-log" class="log"></div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let statusData = {};
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function() {
                log('WebSocket connected');
                requestStatus();
            };
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                if (message.type === 'status') {
                    updateStatus(message.data);
                }
            };
            
            ws.onclose = function() {
                log('WebSocket disconnected. Reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                log('WebSocket error: ' + error);
            };
        }
        
        function requestStatus() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({command: 'get_status'}));
            }
        }
        
        function updateStatus(data) {
            statusData = data;
            
            // Update status indicator
            const statusEl = document.getElementById('status-indicator');
            if (data.running && !data.paused) {
                statusEl.innerHTML = '<span class="status-indicator status-running"></span>🟢 MONITORING';
            } else if (data.paused) {
                statusEl.innerHTML = '<span class="status-indicator status-paused"></span>⏸️ PAUSED';
            } else {
                statusEl.innerHTML = '<span class="status-indicator status-stopped"></span>🔴 STOPPED';
            }
            
            // Update metrics
            document.getElementById('uptime').textContent = formatUptime(data.statistics?.uptime || 0);
            document.getElementById('latest-block').textContent = (data.latest_network_block || 0).toLocaleString();
            document.getElementById('processed-block').textContent = (data.last_processed_block || 0).toLocaleString();
            document.getElementById('processing-lag').textContent = `${data.processing_lag || 0} blocks`;
            document.getElementById('processing-rate').textContent = `${(data.statistics?.blocks_per_minute || 0).toFixed(2)}/min`;
            document.getElementById('blocks-processed').textContent = (data.statistics?.blocks_processed || 0).toLocaleString();
            document.getElementById('transactions').textContent = (data.statistics?.transactions_processed || 0).toLocaleString();
            document.getElementById('events').textContent = (data.statistics?.events_processed || 0).toLocaleString();
            document.getElementById('errors').textContent = data.statistics?.errors || 0;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            // Update button states
            updateButtons(data);
        }
        
        function updateButtons(data) {
            const startBtn = document.getElementById('start-btn');
            const pauseBtn = document.getElementById('pause-btn');
            const resumeBtn = document.getElementById('resume-btn');
            const stopBtn = document.getElementById('stop-btn');
            
            startBtn.disabled = data.running;
            pauseBtn.disabled = !data.running || data.paused;
            resumeBtn.disabled = !data.running || !data.paused;
            stopBtn.disabled = !data.running;
        }
        
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        function log(message) {
            const logEl = document.getElementById('activity-log');
            const timestamp = new Date().toLocaleTimeString();
            logEl.innerHTML += `[${timestamp}] ${message}<br>`;
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        async function apiCall(endpoint, method = 'POST') {
            try {
                const response = await fetch(`/api/${endpoint}`, {
                    method: method,
                    headers: {'Content-Type': 'application/json'}
                });
                const result = await response.json();
                if (result.success) {
                    log(result.message);
                } else {
                    log(`Error: ${result.error}`);
                }
                requestStatus();
            } catch (error) {
                log(`API Error: ${error}`);
            }
        }
        
        function startMonitor() { apiCall('start'); }
        function pauseMonitor() { apiCall('pause'); }
        function resumeMonitor() { apiCall('resume'); }
        function stopMonitor() { apiCall('stop'); }
        
        // Initialize
        connectWebSocket();
        setInterval(requestStatus, 5000);  // Update every 5 seconds
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')
        
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'GLQ Chain Monitoring Service',
            'version': '1.0.0'
        })
        
    async def _get_status_data(self) -> Dict[str, Any]:
        """Get status data for internal use."""
        if self.monitor:
            return self.monitor.get_status()
        return {
            'service_status': 'not_initialized',
            'running': False,
            'paused': False
        }
        
    async def _run_monitor(self):
        """Run monitor in background task."""
        try:
            if not await self.monitor.initialize():
                logger.error("Failed to initialize monitor")
                return
                
            await self.monitor.start_monitoring()
        except Exception as e:
            logger.error(f"Monitor task failed: {e}")
            
    async def broadcast_status(self):
        """Broadcast status updates to all connected WebSocket clients."""
        if not self.websocket_connections:
            return
            
        try:
            status = await self._get_status_data()
            message = json.dumps({'type': 'status', 'data': status}, cls=DateTimeEncoder)
            
            # Send to all connected clients
            disconnected = set()
            for ws in self.websocket_connections:
                try:
                    await ws.send_str(message)
                except Exception:
                    disconnected.add(ws)
                    
            # Remove disconnected clients
            for ws in disconnected:
                self.websocket_connections.discard(ws)
                
        except Exception as e:
            logger.error(f"Error broadcasting status: {e}")
            
    async def start_service(self):
        """Start the monitoring service."""
        logger.info(f"Starting monitoring service on port {self.port}")
        
        # Start background task for WebSocket broadcasts
        self._broadcast_task = asyncio.create_task(self._websocket_broadcast_loop())
        
        # Start web server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Monitoring service running on http://localhost:{self.port}")
        logger.info(f"Dashboard available at: http://localhost:{self.port}/dashboard")
        
    async def _websocket_broadcast_loop(self):
        """Background task to broadcast status updates."""
        while True:
            try:
                await self.broadcast_status()
                await asyncio.sleep(2)  # Broadcast every 2 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")
                await asyncio.sleep(5)
                
    async def shutdown(self):
        """Graceful shutdown of the service."""
        logger.info("Shutting down monitoring service...")
        
        # Cancel broadcast task
        if hasattr(self, '_broadcast_task'):
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Stop monitor
        if self.monitor:
            await self.monitor.stop_monitoring()
            
        # Close WebSocket connections
        for ws in self.websocket_connections.copy():
            await ws.close()
            
        # Cleanup web server
        if hasattr(self, 'runner'):
            await self.runner.cleanup()
            
        logger.info("Monitoring service shutdown complete")


async def main():
    """Main function to start the monitoring service."""
    import os
    import logging
    from datetime import datetime
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/monitoring_service.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = Config()
    
    # Create and start service
    service = MonitoringService(config, port=8001)
    
    try:
        await service.start_service()
        logger.info("Service started successfully. Press Ctrl+C to stop.")
        
        # Keep service running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
    finally:
        logger.info("Starting shutdown...")
        await service.shutdown()
        logger.info("Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
