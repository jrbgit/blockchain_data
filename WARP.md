# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **Multi-Chain Blockchain Analytics Platform** that monitors and analyzes blockchain data across multiple networks including GLQ Chain (GraphLinq), Ethereum, Polygon, Base, Avalanche, and BNB Smart Chain. The system provides real-time monitoring, historical data processing, and comprehensive analytics for DeFi, DEX, and general blockchain activity.

**Environment**: This project is optimized for **Linux/WSL (Windows Subsystem for Linux)** environments and has been migrated from Windows to ensure better compatibility and performance.

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

## Development Environment Setup

### Prerequisites (Linux/WSL)

- **Operating System**: Ubuntu 20.04+ or compatible Linux distribution
- **WSL**: WSL2 recommended for Windows users
- **Python**: Python 3.12+ (`sudo apt install python3.12 python3.12-venv`)
- **Git**: Version control (`sudo apt install git`)
- **Docker**: For running InfluxDB and GLQ Chain nodes

### Initial Environment Setup

```bash
# Clone repository (if needed)
git clone <repository-url>
cd blockchain_data

# Create and activate Python virtual environment (Linux/WSL compatible)
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your InfluxDB token and Infura project ID
```

### Virtual Environment Management (CRITICAL)

**Important**: If migrating from Windows to WSL/Linux, the existing virtual environment must be recreated due to different binary formats.

```bash
# Remove old Windows venv (if migrating)
rm -rf venv

# Create new Linux-compatible venv
python3 -m venv venv

# Always activate before working
source venv/bin/activate

# Verify activation (should show path in venv)
which python

# Install/reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt
```bash

## Common Development Commands

### Environment Activation (Always First!)

```bash
# ALWAYS run this before any development work
source venv/bin/activate

# Verify virtual environment is active
which python  # Should show: /path/to/blockchain_data/venv/bin/python
```bash

### Database Setup

```bash
# InfluxDB should be running at http://localhost:8086
# Create organization: glq-analytics
# Create bucket: blockchain_data
# Generate API token and add to .env file
```bash

### Testing and Validation

```bash
# Test multi-chain connectivity
python test_multichain_simple.py

# Test system setup (legacy GLQ only)
python tests/test_sync_setup.py

# Test specific components
python test_analytics_integration.py
python test_monitor.py
```

### Data Synchronization

```bash
# Full multi-chain historical sync (all configured chains)
python glq_analytics.py sync

# Sync specific chains only
python glq_analytics.py sync --chains ethereum,polygon,glq

# Limit sync for testing (1000 blocks per chain)
python glq_analytics.py sync --max-blocks 1000

# Legacy GLQ-only sync
python glq_analytics.py legacy sync
```bash

### Real-time Monitoring

```bash
# Start multi-chain real-time monitoring
python glq_analytics.py monitor

# Monitor specific chains
python glq_analytics.py monitor --chains glq,ethereum

# Start web dashboard service
python glq_analytics.py service
# Then visit: http://localhost:8000/dashboard

# Legacy monitoring
python glq_analytics.py legacy monitor
```bash

### Running Tests

```bash
# Unit tests
pytest tests/

# Integration tests
python test_multichain.py
python test_analytics_fixes.py

# Report generation tests
python test_report_generation.py
```bash

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

### Linux/WSL Specific Considerations

#### File Permissions

```bash
# Make scripts executable if needed
chmod +x glq_analytics.py
chmod +x scripts/*.py

# Check file permissions
ls -la
```bash

#### Path Handling

- Use forward slashes `/` for all paths (Linux standard)
- Avoid Windows-specific path constructions
- Use `os.path.join()` or `pathlib.Path` for cross-platform compatibility

#### Environment Variables

```bash
# Check current environment
env | grep INFLUX
env | grep INFURA

# Set temporary environment variables
export INFLUX_TOKEN="your_token_here"
export MAX_WORKERS=8
```bash

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

### System Requirements (Linux/WSL)

- **OS**: Ubuntu 20.04+ or compatible Linux distribution
- **Python**: 3.12+ with venv support
- **Memory**: 8GB+ RAM recommended for full sync
- **Storage**: SSD storage for database performance
- **Docker**: For InfluxDB and blockchain nodes

### Configuration for Production

- Set appropriate `MAX_WORKERS` based on system capabilities
- Configure retention policies in InfluxDB
- Set up proper logging rotation
- Use environment variables for all sensitive data
- Configure monitoring alerts

### Performance Benchmarks (Linux/WSL)

- **Historical Sync**: 67+ blocks/second processing rate
- **Real-time Monitoring**: 2-second polling with sub-second processing
- **Memory Usage**: ~4GB during full historical sync
- **Database Growth**: ~1GB per million blocks processed

## Troubleshooting

### Common Linux/WSL Issues

#### Virtual Environment Problems

```bash
# If venv activation fails
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```bash

#### Permission Errors

```bash
# Fix file permissions
chmod +x glq_analytics.py
chmod +x scripts/*.py

# Check current permissions
ls -la glq_analytics.py
```bash

#### Python Path Issues

```bash
# Check Python version and location
python3 --version
which python3
which python  # Should show venv path when activated
```bash

#### Package Installation Issues

```bash
# Update package manager
sudo apt update
sudo apt upgrade

# Install Python development headers if needed
sudo apt install python3-dev python3.12-dev

# Reinstall pip
python -m pip install --upgrade pip
```bash

### Environment Migration Checklist

When migrating from Windows to Linux/WSL:

- [ ] Remove old Windows `venv` directory: `rm -rf venv`
- [ ] Create new Linux venv: `python3 -m venv venv`
- [ ] Activate new venv: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Fix script permissions: `chmod +x *.py scripts/*.py`
- [ ] Update any hardcoded Windows paths in configuration
- [ ] Test all functionality with `python glq_analytics.py test`
- [ ] Verify web dashboard access at `http://localhost:8000/dashboard`

## Current Status

### ✅ Linux/WSL Migration Complete

- Virtual environment recreated for Linux compatibility
- All dependencies reinstalled and verified
- File permissions updated for Linux environment
- Documentation updated with Linux-specific instructions
- Cross-platform compatibility maintained

### System Performance (Post-Migration)

- **Processing Rate**: 67+ blocks/second maintained
- **Real-time Monitoring**: 2-second polling active
- **Web Dashboard**: Fully functional at localhost:8000
- **Database Operations**: All InfluxDB operations verified
- **Multi-chain Support**: All configured chains operational

This system represents a production-ready blockchain analytics platform capable of handling multi-chain data processing at scale with comprehensive monitoring and analytics capabilities, now fully optimized for Linux/WSL environments.

## Migration Success Summary

**✅ WINDOWS → LINUX/WSL MIGRATION COMPLETED**

1. **Environment Compatibility**: Full Linux/WSL support implemented
2. **Virtual Environment**: Recreated with Linux-compatible binaries
3. **Dependencies**: All packages reinstalled and verified working
4. **File Permissions**: Updated for Linux filesystem
5. **Documentation**: Comprehensive Linux-specific guidance added
6. **Performance**: All benchmarks maintained or improved
7. **Functionality**: Zero downtime migration, all features operational

The system is now fully operational in the Linux/WSL environment with enhanced compatibility and maintainability.
