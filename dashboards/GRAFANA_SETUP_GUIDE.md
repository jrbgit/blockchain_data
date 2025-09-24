# Grafana Dashboard Setup Guide

## Multi-Chain Blockchain Analytics Dashboard

This guide will help you set up the Grafana dashboard to visualize your multi-chain blockchain analytics data from InfluxDB.

## Prerequisites

1. **InfluxDB 2.x** running at `http://localhost:8086`
2. **Grafana** running (typically at `http://localhost:3000`)
3. **Blockchain analytics data** in your InfluxDB `blockchain_data` bucket

## Step 1: Install and Start Grafana

### Option A: Using Docker
```bash
docker run -d \
  -p 3000:3000 \
  --name=grafana \
  -e "GF_INSTALL_PLUGINS=grafana-influxdb-datasource" \
  grafana/grafana-enterprise
```

### Option B: Using Local Installation
- Download Grafana from https://grafana.com/grafana/download
- Follow platform-specific installation instructions
- Start Grafana service

## Step 2: Configure InfluxDB Data Source

1. **Open Grafana** in your browser: `http://localhost:3000`
2. **Login** with default credentials: `admin/admin`
3. **Go to Configuration → Data Sources**
4. **Click "Add data source"**
5. **Select "InfluxDB"**

### InfluxDB Configuration Settings:
```
Query Language: Flux
URL: http://localhost:8086
Access: Server (default)
Skip TLS Verify: true (for local development)

InfluxDB Details:
Organization: glq-analytics
Token: [Your InfluxDB API token from .env file]
Default Bucket: blockchain_data
```

6. **Test & Save** the connection

## Step 3: Import the Dashboard

1. **Go to Create → Import** (+ icon → Import)
2. **Upload the JSON file**: `dashboards/multi-chain-blockchain-analytics.json`
   - Or copy-paste the JSON content directly
3. **Configure the dashboard**:
   - **Name**: Multi-Chain Blockchain Analytics
   - **Folder**: Choose or create a folder
   - **UID**: Leave blank (auto-generate)
4. **Select the InfluxDB data source** you configured in Step 2
5. **Click Import**

## Step 4: Configure Dashboard Variables

The dashboard includes a chain filter variable that should automatically populate with available chains from your data.

If the variable doesn't populate:
1. Go to **Dashboard Settings** (gear icon)
2. Go to **Variables**
3. Edit the **chain** variable
4. Verify the query: 
   ```flux
   from(bucket: "blockchain_data") 
   |> range(start: -1h) 
   |> filter(fn: (r) => r["_measurement"] == "blocks") 
   |> keyValues(keyColumns: ["chain"]) 
   |> group() 
   |> distinct(column: "chain")
   ```

## Dashboard Features

### 📊 **Included Panels:**

1. **Chain Status Overview** - Number of active chains
2. **Latest Block Numbers** - Current block heights per chain
3. **Blocks Per Second** - Real-time block processing rates
4. **Transaction Volume by Chain** - 24h transaction counts
5. **Average Gas Usage by Chain** - Gas consumption patterns
6. **Block Time Distribution** - Block timing analysis
7. **Top Active Addresses** - Most active wallet addresses
8. **Token Transfers by Chain** - ERC token transfer activity
9. **Contract Deployments** - New contract deployments
10. **Network Activity Heatmap** - 7-day activity visualization
11. **DEX Activity Overview** - DEX swap activity
12. **Cross-Chain Comparison** - Chain comparison metrics

### 🎛️ **Interactive Features:**
- **Time Range Selector**: Adjustable time windows
- **Chain Filter**: Filter by specific blockchain(s)
- **Auto Refresh**: 10-second refresh interval
- **Drill-down**: Click on panels for detailed views

## Troubleshooting

### No Data Showing
1. **Verify InfluxDB connection**:
   ```bash
   curl -H "Authorization: Token YOUR_TOKEN" \
        "http://localhost:8086/api/v2/buckets?org=glq-analytics"
   ```

2. **Check data exists**:
   ```bash
   # Test query in InfluxDB UI
   from(bucket: "blockchain_data")
   |> range(start: -1h)
   |> filter(fn: (r) => r._measurement == "blocks")
   |> limit(n: 10)
   ```

3. **Verify measurement names** in your data match the dashboard queries

### Dashboard Shows Errors
1. **Check Grafana logs** for detailed error messages
2. **Verify InfluxDB token permissions** (read access to blockchain_data bucket)
3. **Test individual panel queries** in Grafana's query editor

### Performance Issues
1. **Adjust time ranges** for large datasets
2. **Increase aggregation windows** (change `every: 1m` to `every: 5m`)
3. **Add data retention policies** to InfluxDB

## Customization

### Adding New Panels
1. **Click "Add panel"** in dashboard edit mode
2. **Configure data source** and query
3. **Choose visualization type**
4. **Set panel options** and styling

### Example Custom Query (Top Gas Consumers):
```flux
from(bucket: "blockchain_data")
|> range(start: -24h)
|> filter(fn: (r) => r._measurement == "transactions" and r._field == "gas_used")
|> group(columns: ["from", "chain"])
|> sum()
|> sort(columns: ["_value"], desc: true)
|> limit(n: 10)
```

### Modifying Existing Panels
1. **Enter edit mode** (pencil icon)
2. **Click on panel title** → Edit
3. **Modify queries**, visualization, or styling
4. **Save changes**

## Advanced Configuration

### Setting up Alerts
1. **Go to Alerting → Alert Rules**
2. **Create alert rules** for key metrics
3. **Configure notification channels** (email, Slack, etc.)

Example alert: "Block processing lag > 10 blocks"

### Creating Additional Dashboards
Consider creating specialized dashboards for:
- **DeFi Analytics**: Focus on DEX swaps, liquidity, yield farming
- **Token Analytics**: ERC-20/721 transfers, holder analysis
- **Network Health**: Node status, processing metrics
- **Security Monitoring**: Unusual transaction patterns

## Integration with Your Analytics Platform

The dashboard is designed to work with your multi-chain blockchain analytics platform:

- **Real-time Updates**: Dashboard refreshes every 10 seconds
- **Multi-Chain Support**: Automatically detects all configured chains
- **Scalable**: Handles data from GLQ, Ethereum, Polygon, Base, Avalanche, BSC
- **Extensible**: Easy to add new metrics and visualizations

## Data Source Mapping

The dashboard expects these InfluxDB measurements:
- `blocks`: Block-level data
- `transactions`: Transaction details
- `token_transfers`: ERC token transfers
- `contracts`: Smart contract data
- `dex_swaps`: DEX activity (when available)
- `network_metrics`: Aggregated statistics

Make sure your analytics platform is writing to these measurement names.

---

## 🚀 Quick Start Summary

1. **Start Grafana**: `http://localhost:3000`
2. **Add InfluxDB data source**: URL `http://localhost:8086`, Org `glq-analytics`
3. **Import dashboard**: Upload `multi-chain-blockchain-analytics.json`
4. **Verify data**: Check that panels show your blockchain data
5. **Customize**: Adjust time ranges, filters, and add custom panels

Your multi-chain blockchain analytics dashboard is now ready! 📊