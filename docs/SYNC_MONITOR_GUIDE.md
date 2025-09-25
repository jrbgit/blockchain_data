# GLQ Chain Sync Progress Monitor - Usage Guide

## 🎯 Purpose

This advanced monitoring script provides real-time tracking of your blockchain synchronization progress after running `reset_and_sync.py`. It offers comprehensive insights into sync performance, system health, and analytics processing.

## 🚀 Quick Start

### Option 1: Using the Batch File (Recommended for Windows)
```bash
# Double-click or run from command prompt
monitor_sync_progress.bat
```

### Option 2: Direct Python Execution
```bash
# Make sure you're in the blockchain_data directory
python sync_progress_monitor.py
```

## 📊 Dashboard Features

The monitor displays a comprehensive real-time dashboard with:

### 1. **Sync Progress Panel** 📊
- **Current Block**: Latest block synchronized to database
- **Total Blocks**: Total blocks available on the network
- **Progress Percentage**: Completion percentage
- **Sync Rate**: Current synchronization speed (blocks/second)
- **ETA**: Estimated time to completion

### 2. **Analytics Progress Panel** 🔬
Shows processing status for different types of blockchain analytics:
- **📦 Blocks**: Core block data
- **💸 Transactions**: Transaction details
- **🪙 Token Transfers**: ERC-20/721/1155 transfer events
- **🔄 DEX Swaps**: Decentralized exchange activity
- **💧 Liquidity Events**: DeFi liquidity changes
- **🏦 DeFi Events**: DeFi protocol interactions
- **📜 Contract Deployments**: Smart contract deployments

### 3. **System Health Panel** 💻
Monitors system resources:
- **CPU Usage**: Current processor utilization
- **Memory Usage**: RAM consumption
- **Disk Usage**: Storage space utilization
- **Health Alerts**: Automatic warnings for resource issues

### 4. **Performance History Panel** 📈
Tracks recent performance metrics:
- **Time**: Timestamp of measurement
- **Block**: Block number at that time
- **Rate/sec**: Synchronization speed
- **CPU%**: Processor usage
- **Mem%**: Memory usage

## ⚙️ Configuration

The monitor automatically detects:
- InfluxDB connection settings from your `.env` file
- GLQ Chain RPC connection from `config/config.yaml`
- Running sync processes

## 🔍 What to Monitor

### Normal Operation Indicators
- ✅ **Sync Rate**: 20-100+ blocks/second (depending on system)
- ✅ **CPU Usage**: 30-80% during sync
- ✅ **Memory Usage**: < 80% of available RAM
- ✅ **Analytics Active**: Various analytics showing "✅ Active" status

### Warning Signs
- ⚠️ **Low Sync Rate**: < 10 blocks/second for extended periods
- ⚠️ **High Resource Usage**: CPU/Memory > 90%
- ⚠️ **Connection Issues**: Unable to retrieve sync data
- ⚠️ **Disk Space**: < 10% free space remaining

## 🎛️ Controls

- **Real-time Updates**: Dashboard refreshes every 3 seconds
- **Exit**: Press `Ctrl+C` to stop monitoring
- **Auto-completion**: Monitor automatically detects when sync is complete

## 🚨 Troubleshooting

### Monitor Won't Start
1. **Check Dependencies**: Ensure `rich` and `psutil` are installed
   ```bash
   pip install rich psutil
   ```

2. **Check Configuration**: Verify your `.env` file has `INFLUX_TOKEN` set

3. **Check Connections**: Ensure GLQ Chain node and InfluxDB are running

### No Sync Data
1. **Verify Sync Running**: Check if `reset_and_sync.py` or similar is actually running
2. **Check Database**: Ensure InfluxDB is accessible and has data
3. **Check Logs**: Look at log files in the `logs/` directory

### Performance Issues
1. **High CPU**: Consider reducing batch size in sync configuration
2. **High Memory**: Monitor memory usage and restart if needed
3. **Slow Sync**: Check network connectivity and blockchain node health

## 📈 Expected Performance

### Typical Sync Rates
- **Fast System**: 50-100+ blocks/second
- **Average System**: 20-50 blocks/second  
- **Slower System**: 10-25 blocks/second

### Sync Duration Estimates
Based on ~5.4M blocks in GLQ Chain:
- **Fast (75 blocks/sec)**: ~20 hours
- **Average (35 blocks/sec)**: ~43 hours
- **Slower (15 blocks/sec)**: ~100 hours

## 🎉 Sync Completion

When sync is complete, the monitor will:
1. Display "🎉 SYNC COMPLETE!" message
2. Show completion time
3. Provide next steps for using your synced data
4. Automatically exit after 30 seconds

## 📞 Next Steps After Sync

Once sync is complete:

1. **Start Real-time Monitoring**:
   ```bash
   python glq_analytics.py monitor
   ```

2. **Launch Web Dashboard**:
   ```bash
   python scripts/start_monitor_service.py
   ```

3. **Generate Analytics Reports**:
   ```bash
   python start_multichain_monitor.py --mode analytics
   ```

## 💡 Tips

1. **Run in Background**: You can minimize the terminal and let it run
2. **Monitor Remotely**: SSH into your machine to check progress
3. **Multiple Terminals**: Use one for sync, another for monitoring
4. **Save Logs**: The sync process saves detailed logs in `logs/` directory
5. **System Resources**: Ensure adequate CPU, RAM, and disk space before starting

## 🔧 Advanced Usage

### Custom Refresh Rate
```bash
# Modify the refresh_interval in the script (default: 3 seconds)
monitor = AdvancedSyncMonitor(refresh_interval=5)  # 5-second updates
```

### Monitoring Specific Analytics
The script automatically detects which analytics modules are active and shows their processing status.

## 📱 Integration

This monitor can run alongside:
- The main sync process (`reset_and_sync.py`)
- Multi-chain operations (`multichain_cli.py`)
- Web dashboard (`scripts/start_monitor_service.py`)
- Real-time monitoring (`glq_analytics.py monitor`)

---

**Happy Monitoring!** 🚀

For issues or questions, check the main project documentation or examine the log files in the `logs/` directory.