# Advanced Analytics Modules Documentation

This document provides comprehensive information about the advanced analytics modules in the GLQ Chain Analytics Platform.

## 🚀 Overview

The analytics system consists of four main components:

1. **Token Analytics** - ERC20/721/1155 token transfer tracking
2. **DEX Analytics** - Decentralized exchange trading analysis  
3. **DeFi Analytics** - DeFi protocol interaction monitoring
4. **Advanced Analytics Coordinator** - Orchestrates all analytics modules

## 🪙 Token Analytics Module

### Features
- **Multi-Standard Support**: ERC20, ERC721, ERC1155 token transfers
- **Automatic Detection**: Smart contract event signature recognition
- **Token Information**: Contract metadata caching and retrieval
- **Volume Metrics**: Transfer volumes, unique holders, activity patterns

### Event Signatures Detected
```solidity
// ERC20/ERC721 Transfer
Transfer(address indexed from, address indexed to, uint256 value/tokenId)
// Signature: 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef

// ERC1155 TransferSingle  
TransferSingle(address indexed operator, address indexed from, address indexed to, uint256 id, uint256 value)
// Signature: 0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62

// ERC1155 TransferBatch
TransferBatch(address indexed operator, address indexed from, address indexed to, uint256[] ids, uint256[] values)
// Signature: 0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb
```

### Data Storage
**Measurement**: `token_transfers`

**Tags**:
- `tx_hash` - Transaction hash
- `token_address` - Token contract address
- `token_type` - Token standard (ERC20, ERC721, ERC1155)
- `from_address` - Sender address
- `to_address` - Recipient address

**Fields**:
- `block_number` - Block number (integer)
- `log_index` - Log index within transaction (integer)
- `value` - Transfer amount/quantity (integer)
- `token_id` - Token ID for NFTs (integer)

### Usage Example
```python
from analytics.token_analytics import TokenAnalytics

# Initialize
token_analytics = TokenAnalytics(blockchain_client, db_client, config)

# Analyze transaction logs
transfers = await token_analytics.analyze_transaction_logs(tx_data, receipt, block_timestamp)

# Store results
token_analytics.store_token_transfers(transfers)

# Calculate metrics
metrics = await token_analytics.calculate_token_metrics("0x742...", "24h")
```

## 💱 DEX Analytics Module

### Features
- **Multi-DEX Support**: Uniswap V2, Uniswap V3, SushiSwap compatible
- **Swap Detection**: Automated swap event parsing and analysis
- **Liquidity Tracking**: LP provision and removal monitoring
- **Trading Metrics**: Volume, pair analytics, price impact calculations

### Supported DEX Types

#### Uniswap V2 Style
```solidity
// Swap Event
Swap(address indexed sender, uint amount0In, uint amount1In, uint amount0Out, uint amount1Out, address indexed to)
// Signature: 0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822

// Liquidity Events
Mint(address indexed sender, uint amount0, uint amount1)
// Signature: 0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f

Burn(address indexed sender, uint amount0, uint amount1, address indexed to)
// Signature: 0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496
```

#### Uniswap V3 Style  
```solidity
// Swap Event (simplified)
Swap(address indexed sender, address indexed recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)
// Signature: 0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67
```

### Data Storage

**DEX Swaps Measurement**: `dex_swaps`
- Tags: `tx_hash`, `dex_address`, `dex_type`, `sender`, `recipient`, `token_in`, `token_out`
- Fields: `block_number`, `amount_in`, `amount_out`, `price_impact`

**Liquidity Events Measurement**: `dex_liquidity`  
- Tags: `tx_hash`, `dex_address`, `event_type`, `provider`, `token0`, `token1`
- Fields: `block_number`, `amount0`, `amount1`, `liquidity_delta`

### Usage Example
```python
from analytics.dex_analytics import DEXAnalytics

# Initialize
dex_analytics = DEXAnalytics(blockchain_client, db_client, config)

# Analyze DEX activities
swaps, liquidity_events = await dex_analytics.analyze_dex_logs(tx_data, receipt, block_timestamp)

# Store results
dex_analytics.store_swaps(swaps)
dex_analytics.store_liquidity_events(liquidity_events)
```

## 🏦 DeFi Analytics Module

### Features
- **Lending Protocols**: Compound, Aave compatible event parsing
- **Staking Systems**: Validator and protocol staking monitoring
- **Yield Farming**: Pool interactions and reward tracking
- **Protocol Metrics**: TVL, utilization rates, APY calculations

### Supported Protocols

#### Lending Protocols
- **Compound Style**: Supply, withdraw, borrow, repay events
- **Aave Style**: Deposit, withdraw, borrow, repay events
- **Custom Protocols**: Configurable via contract addresses

#### Staking Protocols
- **Validator Staking**: ETH 2.0 style staking
- **Protocol Staking**: Token staking for rewards
- **Delegation**: Stake delegation tracking

#### Yield Farming
- **Pool Operations**: Deposits, withdrawals, harvests
- **Reward Distribution**: Token reward tracking
- **Compounding**: Auto-compound event detection

### Event Signatures
```solidity
// Lending - Supply/Deposit
// Compound: Mint(address minter, uint mintAmount, uint mintTokens)
// Aave: Supply(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referral)

// Lending - Withdraw
// Compound: Redeem(address redeemer, uint redeemAmount, uint redeemTokens)
// Aave: Withdraw(address indexed reserve, address indexed user, address indexed to, uint256 amount)

// Staking - Deposit
// Deposit(address indexed user, uint256 amount)

// Yield Farming - Harvest
// Harvest(address indexed user, uint256 amount)
```

### Data Storage

**DeFi Lending Measurement**: `defi_lending`
- Tags: `protocol`, `event_type`, `user_address`, `token_address`
- Fields: `amount`, `interest_rate`, `collateral_factor`, `health_factor`

**DeFi Staking Measurement**: `defi_staking`
- Tags: `protocol`, `event_type`, `staker_address`, `validator_address`
- Fields: `amount`, `reward_amount`, `lock_period`, `apr`

**DeFi Yield Measurement**: `defi_yield`
- Tags: `protocol`, `event_type`, `farmer_address`, `pool_address`
- Fields: `amount`, `pool_share`, `apy`

### Usage Example
```python
from analytics.defi_analytics import DeFiAnalytics

# Initialize  
defi_analytics = DeFiAnalytics(blockchain_client, db_client, config)

# Analyze DeFi activities
lending, staking, yield_events = await defi_analytics.analyze_defi_logs(tx_data, receipt, block_timestamp)

# Store results
defi_analytics.store_lending_events(lending)
defi_analytics.store_staking_events(staking)
defi_analytics.store_yield_events(yield_events)
```

## 🎛️ Advanced Analytics Coordinator

### Features
- **Module Orchestration**: Coordinates all analytics modules
- **Configuration Management**: Enable/disable modules via config
- **Performance Tracking**: Statistics and performance metrics
- **Batch Processing**: Efficient processing of multiple transactions

### Configuration
Enable/disable analytics modules in `config/config.yaml`:

```yaml
analytics:
  # Token Analytics
  track_erc20_transfers: true
  track_erc721_transfers: true
  track_erc1155_transfers: true
  
  # DEX Analytics
  track_dex_swaps: true
  track_liquidity_changes: true
  
  # DeFi Analytics
  track_lending_protocols: true
  track_yield_farming: true
  track_staking: true
```

### Usage Example
```python
from analytics.advanced_analytics import AdvancedAnalytics

# Initialize
advanced_analytics = AdvancedAnalytics(blockchain_client, db_client, config)

# Analyze single transaction
results = await advanced_analytics.analyze_transaction(tx_data, receipt, block_timestamp)

# Analyze entire block
block_results = await advanced_analytics.analyze_block(block_data, block_timestamp)

# Get processing summary
summary = advanced_analytics.get_analytics_summary()
```

### Processing Statistics
The coordinator tracks comprehensive statistics:

```python
{
    'token_transfers_found': 1247,
    'dex_swaps_found': 342,
    'liquidity_events_found': 89,
    'lending_events_found': 156,
    'staking_events_found': 23,
    'yield_events_found': 67,
    'blocks_processed': 1000,
    'transactions_analyzed': 3421,
    'total_events_found': 1924,
}
```

## 🔧 Integration with Existing Processors

### Decorator Pattern
Add analytics to existing processors:

```python
from analytics.advanced_analytics import add_analytics_to_processor

@add_analytics_to_processor
class MyProcessor:
    def __init__(self, config):
        # Existing initialization
        pass
    
    async def process_single_block(self, block_data, block_number):
        # Existing processing
        # Analytics will be added automatically
        pass
```

### Manual Integration
For custom integration:

```python
from analytics.advanced_analytics import AdvancedAnalytics

class CustomProcessor:
    def __init__(self, config):
        self.analytics = AdvancedAnalytics(
            self.blockchain_client,
            self.db_client, 
            config
        )
    
    async def process_block(self, block_data):
        # Process block normally
        results = await self.process_block_data(block_data)
        
        # Add analytics
        analytics_results = await self.analytics.analyze_block(
            block_data, 
            block_timestamp
        )
        
        return {**results, 'analytics': analytics_results}
```

## 📊 Querying Analytics Data

### InfluxDB Queries

#### Token Transfer Analysis
```flux
from(bucket: "blockchain_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "token_transfers")
  |> filter(fn: (r) => r.token_address == "0x742...")
  |> group(by: ["token_type"])
  |> sum(column: "_value")
```

#### DEX Trading Volume
```flux
from(bucket: "blockchain_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "dex_swaps")
  |> filter(fn: (r) => r.dex_type == "UniswapV2")
  |> group(by: ["token_in", "token_out"])
  |> sum(column: "amount_in")
```

#### DeFi Protocol Activity
```flux
from(bucket: "blockchain_data")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "defi_lending")
  |> filter(fn: (r) => r.protocol == "Compound")
  |> group(by: ["event_type"])
  |> count()
```

### Python Query Examples
```python
# Token metrics
metrics = await token_analytics.calculate_token_metrics("0x742...", "24h")
print(f"Total transfers: {metrics['total_transfers']}")
print(f"Unique users: {metrics['unique_senders'] + metrics['unique_receivers']}")

# DEX metrics  
dex_metrics = await dex_analytics.calculate_dex_metrics("0x123...", "7d")
print(f"Trading volume: {dex_metrics['total_volume_in']}")

# Protocol TVL
tvl_data = await defi_analytics.calculate_tvl_by_protocol()
print(f"Total Value Locked: {sum(tvl_data.values())}")
```

## ⚡ Performance Considerations

### Processing Rates
- **Token Analytics**: ~500-1000 transfers/second
- **DEX Analytics**: ~200-400 swaps/second  
- **DeFi Analytics**: ~100-300 events/second
- **Combined**: ~50-100 blocks/second with full analytics

### Memory Usage
- **Token Analytics**: ~10-50MB per 1000 blocks
- **DEX Analytics**: ~20-100MB per 1000 blocks
- **DeFi Analytics**: ~15-75MB per 1000 blocks
- **Coordinator**: ~5-25MB overhead

### Optimization Tips
1. **Selective Processing**: Disable unused analytics modules
2. **Batch Processing**: Process blocks in batches for efficiency
3. **Memory Management**: Clear caches periodically
4. **Database Optimization**: Use appropriate InfluxDB retention policies

## 🐛 Troubleshooting

### Common Issues

**No Events Detected**
- Check if contract addresses are configured
- Verify event signatures match protocol versions
- Ensure logs are present in transaction receipts

**Memory Usage High**
- Reduce batch sizes in configuration
- Clear analytics caches periodically
- Monitor for memory leaks in custom code

**Slow Processing**
- Disable unused analytics modules
- Optimize database write batches
- Check network latency to blockchain RPC

**Data Quality Issues**
- Validate input data before processing
- Handle edge cases (None values, invalid addresses)
- Implement data quality checks

### Debug Mode
Enable debug logging:

```python
import logging
logging.getLogger('analytics').setLevel(logging.DEBUG)
```

### Testing
Test individual modules:

```bash
# Test token analytics
python src/analytics/token_analytics.py

# Test DEX analytics
python src/analytics/dex_analytics.py

# Test DeFi analytics  
python src/analytics/defi_analytics.py

# Test coordinator
python src/analytics/advanced_analytics.py
```

## 🔮 Future Enhancements

### Planned Features
- **Cross-chain Analytics**: Bridge transaction tracking
- **MEV Detection**: Sandwich attacks, arbitrage detection
- **Gas Optimization**: Gas usage pattern analysis
- **Governance Analytics**: DAO proposal and voting tracking

### Extension Points
- **Custom Protocols**: Add new protocol parsers
- **Advanced Metrics**: Implement custom metric calculations
- **Real-time Alerts**: Add alerting for significant events
- **Machine Learning**: Predictive analytics and anomaly detection

---

This analytics system provides comprehensive blockchain analysis capabilities with high performance and flexibility. For additional questions or custom requirements, please refer to the contributing guidelines or create an issue on GitHub.