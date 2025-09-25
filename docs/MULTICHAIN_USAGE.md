# Multi-Chain Blockchain Analytics System - Usage Guide

## Overview

This system provides comprehensive analytics and monitoring for multiple blockchain networks:
- **GLQ Chain** (GraphLinq Chain) - Local RPC
- **Ethereum Mainnet** - via Infura  
- **Polygon Mainnet** - via Infura
- **Base Mainnet** - via Infura
- **Avalanche C-Chain** - via Infura
- **BNB Smart Chain (BSC)** - via Infura

## 🚀 Quick Start

### 1. System Status
Check if all chains are connected and operational:

```bash
# Basic system status (configuration check)
python multichain_cli.py status

# Test actual connections to all chains
python multichain_cli.py test
```

### 2. Real-Time Monitoring
Start the interactive monitoring dashboard:

```bash
# Basic monitoring (overview mode)
python start_multichain_monitor.py

# Analytics mode with cross-chain comparison
python start_multichain_monitor.py --mode analytics

# Detailed view for specific chains
python start_multichain_monitor.py --mode detailed --chains glq,ethereum

# Performance comparison mode
python start_multichain_monitor.py --mode comparison
```

### 3. Data Synchronization
Sync historical blockchain data:

```bash
# For data sync, use the main analytics script
python glq_analytics.py sync

# Sync specific chains only
python glq_analytics.py sync --chains ethereum,polygon

# Limit blocks per chain (for testing)
python glq_analytics.py sync --chains glq --max-blocks 100
```

## 📊 CLI Commands Reference

### Core Commands

#### `status` - System Status
Shows configured chains and basic system status:

```bash
# Show system configuration
python multichain_cli.py status

# Test actual connections
python multichain_cli.py test
```

**Output:** Table showing chain configuration and connection test results.

#### `sync` - Historical Synchronization  
Downloads and processes historical blockchain data:

```bash
# Sync all chains
multichain.bat sync

# Sync specific chains
multichain.bat sync --chains ethereum,polygon,base

# Limit processing
multichain.bat sync --max-blocks 1000
```

#### `monitor` - Real-time Monitoring
Starts interactive monitoring dashboard:

```bash
# Overview mode (default)
multichain.bat monitor

# Analytics mode
multichain.bat monitor --mode analytics

# Monitor specific chains
multichain.bat monitor --chains glq,ethereum --mode detailed
```

**Available Modes:**
- `overview` - Table summary of all chains
- `detailed` - Individual panels per chain  
- `analytics` - Cross-chain analytics with rankings
- `comparison` - Side-by-side performance metrics

#### `analytics` - Run Analytics
Generates analytics reports:

```bash
# 24-hour analysis (default)
multichain.bat analytics

# Custom timeframe
multichain.bat analytics --hours 48

# Export results  
multichain.bat analytics --hours 24 --export results.json
```

#### `chain` - Individual Chain Operations
Operations for specific chains:

```bash
# Get chain information
multichain.bat chain glq info
multichain.bat chain ethereum info

# Check chain health
multichain.bat chain polygon health

# View recent blocks
multichain.bat chain base blocks --limit 10

# Transaction summary
multichain.bat chain avalanche transactions
```

**Available Operations:**
- `info` - Chain configuration and status
- `health` - Connectivity and responsiveness check
- `blocks` - Recent block information
- `transactions` - Transaction summary

#### `compare` - Chain Comparison
Compare multiple chains side-by-side:

```bash
# Compare all major chains
multichain.bat compare --chains ethereum,polygon,base

# GLQ vs Ethereum comparison  
multichain.bat compare --chains glq,ethereum
```

#### `export` - Data Export
Export analytics data in various formats:

```bash
# Export as JSON
multichain.bat export --format json --output analytics.json

# Export as CSV
multichain.bat export --format csv --output summary.csv --hours 48
```

**Available Formats:** `json`, `csv`

## 📈 Monitoring Dashboard

The monitoring dashboard provides real-time multi-chain visualization:

### Display Modes

1. **Overview Mode** (`--mode overview`)
   - Table with all chains
   - Key metrics: status, latest block, TPS, processing lag
   - Color-coded status indicators

2. **Detailed Mode** (`--mode detailed`)
   - Individual panels per chain
   - Detailed metrics for each chain
   - Transaction and block processing stats

3. **Analytics Mode** (`--mode analytics`)
   - Cross-chain market overview
   - Chain rankings and performance
   - DEX volume and bridge activity

4. **Comparison Mode** (`--mode comparison`)
   - Side-by-side metrics table
   - Performance comparison across chains
   - Relative efficiency analysis

### Dashboard Controls

While in the dashboard:
- **[1]** - Switch to Overview mode
- **[2]** - Switch to Detailed mode  
- **[3]** - Switch to Analytics mode
- **[4]** - Switch to Comparison mode
- **[P]** - Pause/resume monitoring
- **[Q]** - Quit dashboard

## 🔧 Configuration

### Environment Variables
Required environment variables in `.env`:

```bash
# Infura API Key (required for Ethereum, Polygon, Base, Avalanche, BSC)
INFURA_PROJECT_ID=your_infura_project_id_here

# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=blockchain_data

# GLQ Chain RPC (adjust as needed)
GLQ_RPC_URL=http://localhost:8545
```

### Chain Configuration
Chains are configured in `config/config.yaml`:

```yaml
chains:
  glq:
    name: "GraphLinq Chain"
    chain_id: 614
    provider: "local"
    rpc_url: "${GLQ_RPC_URL}"
    enabled: true
    
  ethereum:
    name: "Ethereum Mainnet" 
    chain_id: 1
    provider: "infura"
    enabled: true
    
  # ... other chains
```

## 📋 Common Use Cases

### 1. Daily Monitoring Routine
```bash
# Check system status
multichain.bat status

# Start monitoring dashboard
python start_multichain_monitor.py --mode analytics
```

### 2. Chain Performance Analysis
```bash
# Compare chain performance
multichain.bat compare --chains ethereum,polygon,base

# Get detailed analytics
multichain.bat analytics --hours 48 --export daily_report.json
```

### 3. Troubleshooting Chain Issues
```bash
# Check specific chain health
multichain.bat chain ethereum health

# Get chain information
multichain.bat chain ethereum info

# View recent activity
multichain.bat chain ethereum blocks --limit 5
```

### 4. Historical Data Analysis
```bash
# Sync recent data for analysis
multichain.bat sync --chains ethereum,polygon --max-blocks 1000

# Run comprehensive analytics
multichain.bat analytics --hours 168  # Weekly analysis
```

## 🚨 Troubleshooting

### Common Issues

#### "No chains connected"
1. Check environment variables in `.env`
2. Verify Infura project ID is valid
3. Check GLQ RPC endpoint is accessible
4. Run: `multichain.bat status` for details

#### "Analytics data loading..."
1. Ensure chains are connected and syncing
2. InfluxDB must be running and accessible
3. Check database contains recent data

#### Import/Module Errors
1. Ensure you're in the project root directory
2. Check Python path includes `src/` directory
3. Verify all dependencies are installed

### Logging
Enable verbose logging for troubleshooting:

```bash
# CLI operations
multichain.bat status --verbose

# Monitoring dashboard  
python start_multichain_monitor.py --verbose

# Check log files
cat logs/multichain_monitor.log
```

## 📊 Data Export and Reporting

### Analytics Reports
Generate comprehensive reports:

```python
# Python script for custom reporting
from src.reporting.multichain_reports import generate_daily_report
from src.core.config import Config

config = Config()
report_path = await generate_daily_report(config, 'html')
print(f"Report saved to: {report_path}")
```

### Export Formats
- **JSON**: Complete analytics data structure
- **CSV**: Summary metrics for spreadsheet analysis  
- **HTML**: Formatted report with charts
- **Markdown**: Documentation-friendly format

## 🔄 Regular Maintenance

### Daily Tasks
- Check system status
- Review monitoring dashboard
- Export analytics summary

### Weekly Tasks  
- Generate comprehensive report
- Review chain performance trends
- Check for anomalies or issues

### Monthly Tasks
- Update configuration if needed
- Review and optimize monitoring setup
- Archive historical reports

## 🆘 Support

For issues or questions:
1. Check this usage guide
2. Review log files in `logs/` directory
3. Run commands with `--verbose` flag
4. Test individual chain connections

---

**System Status:** ✅ Multi-chain system operational  
**Supported Chains:** 6 networks (1 local + 5 Infura)  
**Last Updated:** 2025-09-18