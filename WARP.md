# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **Multi-Chain Blockchain Analytics Platform** that monitors and analyzes blockchain data across multiple networks including GLQ Chain (GraphLinq), Ethereum, Polygon, Base, Avalanche, and BNB Smart Chain. The system provides real-time monitoring, historical data processing, and comprehensive analytics for DeFi, DEX, and general blockchain activity.

## Core Architecture

### Multi-Chain Design
The system is built around a **multi-chain architecture** that can simultaneously process data from multiple blockchain networks:
- **Primary Network**: GLQ Chain (local RPC at localhost:8545)
- **External Networks**: Ethereum, Polygon, Base, Avalanche, BSC (via Infura)
- **Unified Data Model**: All chain data flows into a single InfluxDB time-series database
- **Cross-Chain Analytics**: Supports comparative analysis between different blockchain networks

### Key Components
1. **Core Infrastructure** (`src/core/`)
   - `config.py`: Multi-chain configuration management with environment variable substitution
   - `multichain_client.py`: Unified client for all blockchain networks
   - `infura_client.py`: Specialized client for Infura-based chains
   - `multichain_influxdb_client.py`: Time-series database operations

2. **Data Processing** (`src/processors/`)
   - `multichain_processor.py`: Orchestrates multi-chain historical sync and real-time monitoring  
   - `historical_processor.py`: High-performance batch processing (67+ blocks/sec)
   - `realtime_monitor.py`: Live blockchain monitoring with 2-second polling
   - `monitoring_service.py`: Web dashboard service with WebSocket updates

3. **Analytics Modules** (`src/analytics/`)
   - `token_analytics.py`: ERC-20/721/1155 token transfer analysis
   - `dex_analytics.py`: DEX swap detection and liquidity tracking
   - `defi_analytics.py`: DeFi protocol interaction analysis
   - `advanced_analytics.py`: Cross-chain analytics and wallet clustering

## Common Development Commands

### Environment Setup
```powershell
# Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies  
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your InfluxDB token and Infura project ID
```

### Database Setup
```powershell
# InfluxDB should be running at http://localhost:8086
# Create organization: glq-analytics
# Create bucket: blockchain_data
# Generate API token and add to .env file
```

### Testing and Validation
```powershell
# Test multi-chain connectivity
python test_multichain_simple.py

# Test system setup (legacy GLQ only)
python tests/test_sync_setup.py

# Test specific components
python test_analytics_integration.py
python test_monitor.py
```

### Data Synchronization
```powershell
# Full multi-chain historical sync (all configured chains)
python glq_analytics.py sync

# Sync specific chains only
python glq_analytics.py sync --chains ethereum,polygon,glq

# Limit sync for testing (1000 blocks per chain)
python glq_analytics.py sync --max-blocks 1000

# Legacy GLQ-only sync
python glq_analytics.py legacy sync
```

### Real-time Monitoring
```powershell
# Start multi-chain real-time monitoring
python glq_analytics.py monitor

# Monitor specific chains
python glq_analytics.py monitor --chains glq,ethereum

# Start web dashboard service
python glq_analytics.py service
# Then visit: http://localhost:8000/dashboard

# Legacy monitoring
python glq_analytics.py legacy monitor
```

### Running Tests
```powershell
# Unit tests
pytest tests/

# Integration tests
python test_multichain.py
python test_analytics_fixes.py

# Report generation tests
python test_report_generation.py
```

## Configuration Management

### Multi-Chain Configuration (`config/config.yaml`)
The system uses a hierarchical configuration system:
- **chains section**: Defines all supported blockchain networks
- **influxdb section**: Database connection settings  
- **processing section**: Batch sizes, worker counts, real-time settings
- **analytics section**: Feature flags for different analytics modules

### Environment Variables (`.env`)
Critical environment variables:
- `INFLUX_TOKEN`: InfluxDB API token (required)
- `INFURA_PROJECT_ID`: Infura API key for external chains (required)
- `MAX_WORKERS`: Parallel processing workers (default: 8)
- `ENABLED_CHAINS`: Comma-separated chain list (default: all)

### Chain-Specific Settings
Each chain supports:
- Individual enable/disable flags
- Provider-specific RPC/WebSocket URLs
- Network type and chain ID validation
- Rate limiting and timeout configurations

## Data Processing Architecture

### Historical Processing
The system processes historical blockchain data in parallel batches:
- **Batch Size**: 1000 blocks (configurable)
- **Workers**: 8 parallel workers (configurable)  
- **Performance**: 67+ blocks/second achieved
- **Resume Logic**: Automatically resumes from last processed block
- **Memory Management**: Efficient batch processing to handle large datasets

### Real-time Processing
Live monitoring system:
- **Polling Interval**: 2 seconds (configurable)
- **Confirmation Blocks**: 2 block confirmations (configurable)
- **Analytics Integration**: Real-time analytics processing
- **Web Dashboard**: Live updates via WebSocket

### Data Storage Schema
InfluxDB measurements:
- `blocks`: Block-level data (gas usage, timing, transaction counts)
- `transactions`: Individual transaction details with fees and status
- `events`: Smart contract events and logs
- `token_transfers`: ERC token transfer tracking
- `contracts`: Smart contract deployment and interaction data
- `network_metrics`: Aggregated network statistics

## Analytics Capabilities

### Token Analytics
- ERC-20/721/1155 transfer detection and parsing
- Token holder analysis and distribution metrics
- Cross-chain token bridge activity tracking

### DEX Analytics  
- Uniswap V2/V3 swap detection
- Liquidity pool change tracking
- Cross-DEX volume comparisons
- Price impact analysis

### DeFi Analytics
- Lending protocol interaction tracking (Aave, Compound)
- Yield farming activity detection
- Staking and unstaking event analysis
- Cross-protocol flow analysis

### Advanced Analytics
- Wallet clustering algorithms
- Contract popularity scoring
- Cross-chain bridge activity analysis
- MEV detection and analysis

## Development Guidelines

### Adding New Chain Support
1. Add chain configuration to `config/config.yaml`
2. Update environment variables in `.env.example`  
3. Test connectivity with `test_multichain_simple.py`
4. Update documentation and schema files

### Creating Analytics Modules
1. Follow the pattern in `src/analytics/token_analytics.py`
2. Implement proper event signature detection
3. Add configuration flags in `config/config.yaml`
4. Include comprehensive unit tests
5. Update real-time processing integration

### Performance Optimization
- Use async/await patterns for I/O operations
- Implement batch processing for database writes
- Monitor memory usage with large datasets  
- Use connection pooling for blockchain RPC calls
- Implement proper error handling and retry logic

### Testing Strategy
- Unit tests for individual components
- Integration tests for multi-chain operations
- Performance tests with limited block ranges
- End-to-end tests with full sync validation

## Monitoring and Observability

### Web Dashboard
Access the real-time monitoring dashboard at:
- URL: `http://localhost:8000/dashboard`
- Features: Live chain status, processing metrics, recent blocks
- WebSocket updates every 2 seconds

### Log Files
- `logs/multichain_monitor.log`: Real-time monitoring logs
- `logs/historical_processing.log`: Batch processing logs
- `logs/multichain_test.log`: Connectivity test results

### Health Checks
The system includes automated health monitoring:
- Blockchain RPC connectivity
- InfluxDB connection status  
- Processing lag detection
- Error rate monitoring

## Production Deployment

### System Requirements
- Python 3.12+
- InfluxDB 2.x
- 8GB+ RAM recommended for full sync
- SSD storage for database performance

### Configuration for Production
- Set appropriate `MAX_WORKERS` based on system capabilities
- Configure retention policies in InfluxDB
- Set up proper logging rotation
- Use environment variables for all sensitive data
- Configure monitoring alerts

### Performance Benchmarks
- **Historical Sync**: 67+ blocks/second processing rate
- **Real-time Monitoring**: 2-second polling with sub-second processing
- **Memory Usage**: ~4GB during full historical sync
- **Database Growth**: ~1GB per million blocks processed

This system represents a production-ready blockchain analytics platform capable of handling multi-chain data processing at scale with comprehensive monitoring and analytics capabilities.