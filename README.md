# GraphLinq Chain Blockchain Analytics System

A comprehensive real-time blockchain analytics system for the GraphLinq Chain network. This system extracts, processes, and analyzes blockchain data to provide insights into network activity, transaction patterns, DeFi usage, and more.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- GLQ Chain node running (Docker container `glq-chain`)
- InfluxDB 2.x running (Docker container `lcw-influxdb`)

### Setup Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure InfluxDB**
   - Go to http://localhost:8086
   - Create an organization called `glq-analytics`
   - Create a bucket called `blockchain_data`
   - Generate an API token
   - Copy `.env.template` to `.env` and set your token:
     ```
     INFLUX_TOKEN=your_actual_token_here
     ```

3. **Test the Setup**
   ```bash
   python glq_analytics.py test
   # or directly:
   python tests/test_sync_setup.py
   ```

4. **Run Full Blockchain Sync**
   ```bash
   python glq_analytics.py sync
   ```

## 📊 Current Status

### ✅ Completed Components

1. **Project Structure & Dependencies** - All necessary Python packages and directory structure
2. **InfluxDB Schema Design** - Comprehensive data model for blockchain analytics
3. **Core Blockchain Client** - High-performance RPC client with connection pooling
4. **InfluxDB Integration** - Database client optimized for blockchain data storage
5. **Historical Data Processor** - Complete historical sync (5.45M+ blocks processed)
6. **Real-time Monitoring System** - Live blockchain monitoring with web dashboard

### 🧪 System Test Results
```
✅ Configuration: PASS
✅ Blockchain: PASS (Chain ID: 614, Latest Block: 5.45M+)
✅ InfluxDB: PASS (Ready for data storage)
✅ Historical Processor: PASS (67+ blocks/sec processing rate)
✅ Real-time Monitor: PASS (Live monitoring with web dashboard)
```

## 📁 Project Structure

```
blockchain_data/
├── 📁 src/                    # Core source code
│   ├── 📁 analytics/          # Advanced analytics modules
│   ├── 📁 core/              # Core clients and configuration
│   └── 📁 processors/        # Data processing modules
├── 📁 scripts/               # Executable scripts
│   ├── full_sync_with_analytics.py
│   ├── start_realtime_monitor.py
│   └── start_monitor_service.py
├── 📁 tests/                 # Test files
├── 📁 docs/                  # Documentation
├── 📁 config/                # Configuration files
├── 📁 examples/              # Usage examples
├── glq_analytics.py          # Main entry point
└── requirements.txt          # Dependencies
```

## 🔧 System Architecture

### Data Flow
```
GLQ Chain RPC → Blockchain Client → Data Processors → InfluxDB → Analytics
```

### Core Components

#### 1. Blockchain Client (`src/core/blockchain_client.py`)
- Async HTTP client with connection pooling
- Rate limiting and retry logic
- Batch block retrieval
- Transaction receipt fetching
- Event/log extraction

#### 2. InfluxDB Client (`src/core/influxdb_client.py`)
- Optimized for time-series blockchain data
- Measurements: blocks, transactions, events, token_transfers, contracts, etc.
- Efficient batch writing
- Query capabilities for analytics

#### 3. Historical Processor (`src/processors/historical_clean.py`)
- Parallel batch processing
- Progress tracking with Rich UI
- Resumable processing (checks database for latest block)
- Comprehensive error handling
- Performance metrics

## 📈 Analytics Capabilities

### Current Data Extraction
- **Block Data**: Gas usage, block times, transaction counts
- **Transaction Data**: Gas fees, transaction types, success/failure rates
- **Event Data**: Smart contract events and logs
- **Network Metrics**: Real-time network statistics

### Planned Analytics (Next Phase)
- **Token Analytics**: ERC-20/721/1155 transfer tracking
- **DEX Analytics**: Swap volumes, liquidity changes
- **DeFi Metrics**: Lending, staking, yield farming activity
- **Wallet Clustering**: Related address identification
- **Contract Analytics**: Popular contracts, gas usage patterns

## 🗃️ Data Schema

### InfluxDB Measurements

1. **`blocks`** - Block-level data with gas usage, timing, and metadata
2. **`transactions`** - Individual transaction details with fees and status
3. **`events`** - Smart contract events and logs
4. **`token_transfers`** - ERC token transfer tracking
5. **`contracts`** - Smart contract deployment and interaction data
6. **`network_metrics`** - Aggregated network-wide statistics

See `config/influxdb_schema.md` for complete schema documentation.

## ⚙️ Configuration

### Main Config (`config/config.yaml`)
- Blockchain connection settings
- InfluxDB configuration
- Processing parameters (batch size, workers, etc.)
- Analytics feature flags

### Environment Variables (`.env`)
- `INFLUX_TOKEN` - InfluxDB API token
- `INFLUX_ORG` - InfluxDB organization
- `INFLUX_BUCKET` - InfluxDB bucket name
- `MAX_WORKERS` - Processing parallelism

## 🔄 Processing Performance

### Current Performance (Production)
- **Processing Rate**: ~67 blocks/second (actual achieved)
- **Historical Sync**: 5.45M+ blocks completed (839K+ transactions)
- **Batch Size**: 1000 blocks (configurable)
- **Parallel Workers**: 8 (configurable)
- **Memory Efficient**: Complete sync achieved without issues
- **Real-time Monitoring**: 2-second polling with live dashboard

### Sync Status - COMPLETE ✅
- **Total Blocks Processed**: 5,450,971+ blocks
- **Total Transactions**: 839,575+ transactions
- **Actual Sync Time**: ~22.4 hours (much better than estimated!)
- **Real-time Updates**: Active - processing new blocks as they arrive

## 🚧 Next Development Phase

### Priority 1: Real-time Monitoring ✅ COMPLETE
- [x] Polling-based real-time block monitor
- [x] Immediate processing of new blocks
- [x] Live dashboard with real-time updates

### Priority 2: Advanced Analytics
- [ ] ERC token transfer decoder
- [ ] DEX swap detection and analysis
- [ ] DeFi protocol interaction tracking
- [ ] Wallet clustering algorithms

### Priority 3: Dashboard & Visualization
- [ ] Grafana dashboard setup
- [ ] Key metrics visualization
- [ ] Real-time monitoring alerts
- [ ] Historical trend analysis

### Priority 4: Advanced Features
- [ ] Machine learning for anomaly detection
- [ ] Transaction pattern analysis
- [ ] Network health monitoring
- [ ] Automated reporting

## 📝 Usage Examples

### Run Historical Sync (COMPLETED)
```bash
# Process all historical blocks (COMPLETED - 5.45M+ blocks processed)
python src/processors/historical_clean.py
```

### Start Real-time Monitoring
```bash
# Using main entry point
python glq_analytics.py monitor    # Real-time monitoring
python glq_analytics.py service    # Web dashboard service

# Or directly:
python scripts/start_realtime_monitor.py
python scripts/start_monitor_service.py
# Then visit: http://localhost:8000/dashboard
```

### Test with Limited Blocks
```python
# In historical_clean.py, modify the main() function:
success = await processor.run_historical_processing(max_blocks=1000)
```

### Query Analytics Data
```python
from core.influxdb_client import BlockchainInfluxDB
from core.config import Config

config = Config()
db = BlockchainInfluxDB(...)

# Get recent block data
blocks_df = db.query_block_range(5400000, 5400100)

# Get address activity
activity_df = db.query_address_activity("0x123...", days=7)
```

## 🛠️ Maintenance

### Log Files
- System logs: `logs/test_setup.log`
- Historical processing: `logs/historical_processing.log`
- Application logs: `logs/blockchain_analytics.log`

### Data Retention
- Raw blockchain data: 1 year
- Aggregated analytics: 5 years  
- Real-time monitoring: 30 days

### Health Monitoring
- Blockchain RPC connectivity
- InfluxDB connection status
- Processing lag detection
- Error rate monitoring

## 🤝 Contributing

This system is designed for extensibility. Key areas for contribution:

1. **New Analytics Modules** - Add processors for specific DeFi protocols
2. **Dashboard Components** - Create visualizations for new metrics
3. **Performance Optimizations** - Improve processing speed and efficiency
4. **Data Quality** - Add validation and monitoring features

## 📞 Support & Troubleshooting

### Common Issues

1. **InfluxDB "Organization not found"**
   - Create the organization in InfluxDB UI
   - Verify the token has proper permissions

2. **Blockchain connection failures**
   - Check GLQ chain container is running
   - Verify port 8545 is accessible

3. **Slow processing**
   - Increase `MAX_WORKERS` in `.env`
   - Reduce batch size if memory limited

### Getting Help
- Check logs in `logs/` directory
- Run `python test_setup.py` to verify setup
- Review configuration in `config/config.yaml`

---

## 🎯 Current Status Summary

**MAJOR MILESTONE: Full System Operational!** 🎉

✅ **Production-Ready Analytics Platform:**
- **Complete Historical Data**: 5.45M+ blocks processed (839K+ transactions)
- **Real-time Monitoring**: Live blockchain monitoring with web dashboard
- **High-Performance Processing**: 67+ blocks/sec achieved
- **Zero Downtime**: Robust error handling and automatic recovery
- **Comprehensive Analytics**: Foundation for advanced DeFi/DEX analytics

✅ **System Status: OPERATIONAL**
1. ✅ InfluxDB setup complete with full dataset
2. ✅ Historical sync complete (all 5.45M+ blocks)
3. ✅ Real-time monitoring active and functional
4. ⭯ Advanced analytics modules (next priority)

🚀 **What's Working Right Now:**
- Complete GLQ Chain blockchain history in InfluxDB
- Real-time block processing as new blocks arrive
- Web dashboard at http://localhost:8000/dashboard
- API endpoints for programmatic access
- Command-line monitoring tools

The system is now a **fully operational blockchain analytics platform** capable of handling the complete GLQ Chain dataset with real-time updates. Ready for advanced analytics development!
