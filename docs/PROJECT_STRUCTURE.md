# GLQ Chain Analytics - Project Structure

## 📁 Directory Organization

### Root Level
- `glq_analytics.py` - Main entry point for all operations
- `requirements.txt` - Python dependencies
- `.env.template` / `.env.example` - Environment configuration templates
- `.gitignore` - Git ignore patterns

### 📂 `src/` - Core Source Code
Contains the main application logic organized by functionality.

#### `src/core/`
- `config.py` - Configuration management and validation
- `blockchain_client.py` - GLQ Chain RPC client with connection pooling
- `influxdb_client.py` - InfluxDB client optimized for blockchain data

#### `src/processors/`
- `historical_processor.py` - Historical blockchain data sync
- `historical_clean.py` - Clean version of historical processor
- `realtime_monitor.py` - Real-time blockchain monitoring
- `monitoring_service.py` - Web service for monitoring dashboard

#### `src/analytics/`
- `__init__.py` - Analytics module initialization
- `token_analytics.py` - ERC20/721/1155 token transfer analytics
- `dex_analytics.py` - DEX swap and liquidity analytics
- `defi_analytics.py` - DeFi protocol interaction analytics
- `advanced_analytics.py` - Coordinated analytics processing

### 📂 `scripts/` - Executable Scripts
Entry point scripts for various operations.

- `full_sync_with_analytics.py` - Complete blockchain synchronization with analytics
- `start_realtime_monitor.py` - Start real-time command-line monitoring
- `start_monitor_service.py` - Start web dashboard monitoring service

### 📂 `tests/` - Test Suite
Comprehensive testing and validation scripts.

- `test_sync_setup.py` - Complete system connectivity and setup validation
- `test_setup.py` - Basic setup and connection testing  
- `test_monitor_service.py` - Monitoring service testing

### 📂 `docs/` - Documentation
Project documentation and guides.

- `ANALYTICS.md` - Analytics capabilities and modules documentation
- `FIX_SUMMARY.md` - Technical fix documentation
- `SYNC_SUMMARY.md` - Synchronization completion guide
- `CHANGELOG.md` - Version history and changes
- `CONTRIBUTING.md` - Development contribution guidelines
- `PROJECT_STRUCTURE.md` - This file

### 📂 `config/` - Configuration Files
System configuration and schemas.

- `config.yaml` - Main application configuration
- `influxdb_schema.md` - InfluxDB database schema documentation

### 📂 `examples/` - Usage Examples
Example scripts and usage patterns (to be populated).

### 📂 `logs/` - Application Logs
Runtime logs and debugging information (created at runtime).

## 🚀 Usage Patterns

### Using Main Entry Point (Recommended)
```bash
# Test system setup
python glq_analytics.py test

# Run full blockchain sync
python glq_analytics.py sync

# Start real-time monitoring
python glq_analytics.py monitor

# Start web dashboard
python glq_analytics.py service
```

### Direct Script Execution
```bash
# Run tests directly
python tests/test_sync_setup.py

# Run sync directly
python scripts/full_sync_with_analytics.py

# Start monitoring directly
python scripts/start_realtime_monitor.py
```

## 🔗 Import Path Structure

All scripts automatically add the correct paths:
- `src/` directory is added to Python path for core modules
- Relative imports work correctly from any script location

### Example Import Pattern
```python
# From any script in scripts/ or tests/
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Now can import core modules
from core.config import Config
from core.blockchain_client import BlockchainClient
```

## 📦 Module Organization

### Core Modules (`src/core/`)
- **Configuration Management**: Centralized config loading and validation
- **Blockchain Connectivity**: High-performance RPC client with pooling
- **Database Integration**: Optimized InfluxDB client for time-series data

### Processing Modules (`src/processors/`)
- **Historical Processing**: Batch processing for blockchain history
- **Real-time Processing**: Live blockchain monitoring and processing
- **Service Management**: Web services and health monitoring

### Analytics Modules (`src/analytics/`)
- **Token Analysis**: ERC token transfer tracking and metrics
- **DEX Analysis**: Decentralized exchange activity analysis
- **DeFi Analysis**: DeFi protocol interaction tracking
- **Advanced Coordination**: Orchestrated multi-module analytics

## 🔧 Development Guidelines

### Adding New Modules
1. Place core functionality in appropriate `src/` subdirectory
2. Add tests in `tests/` with corresponding names
3. Create scripts in `scripts/` if new entry points needed
4. Update documentation in `docs/`

### Path Management
- Always use `Path(__file__).parent.parent` to reference project root
- Use relative imports within `src/` modules
- Add proper path setup in standalone scripts

### Configuration
- Add new config options to `config/config.yaml`
- Document schema changes in `config/influxdb_schema.md`
- Update environment template files for new variables

## 📈 Scalability Considerations

### Modular Design
- Each analytics module is independent and can be enabled/disabled
- Processing modules can be run separately or together
- Configuration-driven feature flags for easy management

### Performance Optimization
- Core clients support connection pooling and batching
- Analytics modules process in parallel where possible
- Database writes are optimized with batch operations

### Monitoring and Observability
- Comprehensive logging throughout all modules
- Health check endpoints in monitoring services
- Progress tracking and performance metrics