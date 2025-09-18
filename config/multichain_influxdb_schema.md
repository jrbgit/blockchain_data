# Multi-Chain InfluxDB Schema Design for Blockchain Analytics

## Overview
This document defines the InfluxDB measurements, tags, and fields for storing comprehensive multi-chain blockchain analytics data across GLQ Chain, Ethereum, Polygon, Base, Avalanche, and BSC networks.

## Key Multi-Chain Design Principles

### Chain Identification
Every data point includes standardized chain identification tags:
- `chain_id`: Numerical chain ID (1, 137, 8453, etc.)
- `chain_name`: Human-readable chain name ("Ethereum Mainnet", "Polygon", etc.)
- `network`: Network type ("mainnet", "testnet")
- `provider`: Data source provider ("local", "infura", "alchemy", etc.)

### Data Segmentation
- All measurements support filtering by chain
- Cross-chain queries enabled through unified schema
- Chain-specific retention policies possible
- Enables both single-chain and multi-chain analytics

## Measurements Structure

### 1. `blocks` - Block-level Data (Multi-Chain)
**Tags:**
- `chain_id`: Blockchain numerical ID (1, 137, 614, 8453, 43114, 56)
- `chain_name`: Readable name ("Ethereum Mainnet", "Polygon Mainnet", "GraphLinq Chain", etc.)
- `network`: Network type ("mainnet", "testnet")
- `provider`: Data source ("infura", "local", "alchemy")
- `miner`: Block miner/validator address

**Fields:**
- `block_number`: Block height (integer)
- `timestamp`: Block timestamp (timestamp)
- `gas_limit`: Block gas limit (integer)
- `gas_used`: Gas used in block (integer)
- `transaction_count`: Number of transactions (integer)
- `size`: Block size in bytes (integer)
- `difficulty`: Block difficulty (string/big number)
- `total_difficulty`: Cumulative difficulty (string/big number)
- `base_fee_per_gas`: EIP-1559 base fee (integer, where applicable)
- `block_time`: Time since last block in seconds (float)
- `gas_utilization`: gas_used/gas_limit ratio (float)

### 2. `transactions` - Transaction-level Data (Multi-Chain)
**Tags:**
- `chain_id`: Blockchain numerical ID
- `chain_name`: Readable chain name
- `network`: Network type
- `provider`: Data source provider
- `from_address`: Sender address
- `to_address`: Receiver address (null for contract creation)
- `transaction_type`: "transfer", "contract_call", "contract_creation", "token_transfer"
- `status`: "success", "failed", "pending"

**Fields:**
- `block_number`: Block containing transaction (integer)
- `transaction_index`: Position in block (integer)
- `hash`: Transaction hash (string)
- `nonce`: Transaction nonce (integer)
- `value`: Native currency value transferred (string/big number)
- `gas_limit`: Gas limit set (integer)
- `gas_used`: Actual gas used (integer)
- `gas_price`: Gas price paid (integer)
- `effective_gas_price`: Actual gas price after EIP-1559 (integer)
- `transaction_fee`: Total fee paid (string/big number)
- `input_data_size`: Size of input data (integer)

### 3. `events` - Smart Contract Events/Logs (Multi-Chain)
**Tags:**
- `chain_id`: Blockchain numerical ID
- `chain_name`: Readable chain name
- `network`: Network type
- `provider`: Data source provider
- `contract_address`: Contract emitting the event
- `event_signature`: Event signature hash
- `event_name`: Human readable event name (if known)
- `topic0`: First indexed parameter (event signature)
- `topic1`: Second indexed parameter (if exists)
- `topic2`: Third indexed parameter (if exists)
- `topic3`: Fourth indexed parameter (if exists)

**Fields:**
- `block_number`: Block number (integer)
- `transaction_hash`: Transaction hash (string)
- `log_index`: Log index in transaction (integer)
- `data`: Non-indexed event data (string)
- `decoded_data`: JSON of decoded parameters (string)

### 4. `token_transfers` - ERC-20/721/1155 Transfers (Multi-Chain)
**Tags:**
- `chain_id`: Blockchain numerical ID
- `chain_name`: Readable chain name
- `network`: Network type
- `provider`: Data source provider
- `token_address`: Token contract address
- `token_standard`: "ERC20", "ERC721", "ERC1155"
- `from_address`: Sender address
- `to_address`: Recipient address

**Fields:**
- `block_number`: Block number (integer)
- `transaction_hash`: Transaction hash (string)
- `log_index`: Log index (integer)
- `token_id`: Token ID for NFTs (string, null for ERC-20)
- `amount`: Amount transferred (string/big number)
- `token_name`: Token name (string)
- `token_symbol`: Token symbol (string)
- `token_decimals`: Token decimals (integer)

### 5. `dex_swaps` - DEX Swap Transactions (Multi-Chain)
**Tags:**
- `chain_id`: Blockchain numerical ID
- `chain_name`: Readable chain name
- `network`: Network type
- `provider`: Data source provider
- `dex_name`: DEX protocol name ("uniswap", "sushiswap", "quickswap", "pancakeswap", etc.)
- `pair_address`: Trading pair contract
- `token0_address`: First token address
- `token1_address`: Second token address
- `trader_address`: Address performing swap

**Fields:**
- `block_number`: Block number (integer)
- `transaction_hash`: Transaction hash (string)
- `token0_amount`: Amount of token0 (string)
- `token1_amount`: Amount of token1 (string)
- `price_token0_to_token1`: Exchange rate (float)
- `price_token1_to_token0`: Inverse exchange rate (float)
- `gas_used`: Gas used for swap (integer)
- `transaction_fee`: Fee paid (string)
- `usd_value`: USD value of swap (float, if available)

### 6. `contracts` - Smart Contract Data (Multi-Chain)
**Tags:**
- `chain_id`: Blockchain numerical ID
- `chain_name`: Readable chain name
- `network`: Network type
- `provider`: Data source provider
- `contract_address`: Contract address
- `contract_type`: "token", "dex", "defi", "nft", "bridge", "other"
- `deployer_address`: Contract deployer

**Fields:**
- `deployment_block`: Block when deployed (integer)
- `deployment_transaction`: Deployment tx hash (string)
- `bytecode_size`: Size of contract bytecode (integer)
- `is_verified`: Whether source is verified (boolean)
- `interaction_count`: Number of interactions (integer)
- `gas_consumed_total`: Total gas used by contract (integer)
- `unique_users`: Number of unique interacting addresses (integer)

### 7. `network_metrics` - Network-wide Analytics (Multi-Chain)
**Tags:**
- `chain_id`: Blockchain numerical ID
- `chain_name`: Readable chain name
- `network`: Network type
- `provider`: Data source provider
- `metric_type`: "daily", "hourly", "block_range"
- `period`: Time period identifier

**Fields:**
- `start_block`: Period start block (integer)
- `end_block`: Period end block (integer)
- `avg_block_time`: Average block time (float)
- `total_transactions`: Transaction count (integer)
- `total_gas_used`: Total gas consumed (integer)
- `avg_gas_price`: Average gas price (float)
- `active_addresses`: Unique active addresses (integer)
- `new_contracts`: New contracts deployed (integer)
- `total_value_transferred`: Total native currency transferred (string)

### 8. `cross_chain_metrics` - Cross-Chain Comparison Data
**Tags:**
- `metric_type`: "comparison", "bridge_activity", "tvl_comparison"

**Fields:**
- `chains_compared`: JSON array of chain IDs (string)
- `total_chains`: Number of chains in comparison (integer)
- `total_blocks_processed`: Total blocks across all chains (integer)
- `total_transactions`: Total transactions across all chains (integer)
- `avg_block_time_across_chains`: Average block time across all chains (float)
- `chain_activity_scores`: JSON object with activity scores per chain (string)
- `chain_{chain_id}_latest_block`: Latest block per chain (integer)
- `chain_{chain_id}_tps`: Transactions per second per chain (float)

### 9. `bridge_events` - Cross-Chain Bridge Activity
**Tags:**
- `source_chain_id`: Origin chain ID
- `dest_chain_id`: Destination chain ID
- `bridge_protocol`: Bridge name ("polygon_pos", "optimism_gateway", etc.)
- `token_address`: Token being bridged
- `user_address`: User initiating bridge

**Fields:**
- `block_number`: Block number on source chain (integer)
- `transaction_hash`: Source transaction hash (string)
- `dest_transaction_hash`: Destination transaction hash (string, if completed)
- `amount`: Amount bridged (string)
- `status`: "initiated", "completed", "failed"
- `bridge_fee`: Fee paid for bridging (string)

## Chain-Specific Configurations

### Supported Chains
```yaml
# Chain ID mapping
chains:
  ethereum: 1
  polygon: 137
  base: 8453
  avalanche: 43114
  bsc: 56
  glq: 614
```

### Chain-Specific Features
- **Ethereum**: Full EIP-1559 support, extensive DeFi ecosystem
- **Polygon**: High throughput, Layer 2 scaling, DeFi focus
- **Base**: Coinbase Layer 2, growing ecosystem
- **Avalanche**: C-Chain EVM compatibility, unique consensus
- **BSC**: Binance ecosystem, high volume DEX activity
- **GLQ**: Local chain with custom analytics

## Query Examples

### Single Chain Query
```flux
// Get latest blocks for Ethereum only
from(bucket: "blockchain_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "blocks")
  |> filter(fn: (r) => r["chain_id"] == "1")  // Ethereum only
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 100)
```

### Multi-Chain Comparison
```flux
// Compare transaction volume across all chains
from(bucket: "blockchain_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "network_metrics")
  |> filter(fn: (r) => r["_field"] == "total_transactions")
  |> group(columns: ["chain_name"])
  |> aggregateWindow(every: 1h, fn: sum, createEmpty: false)
```

### Cross-Chain Bridge Activity
```flux
// Monitor Ethereum to Polygon bridge activity
from(bucket: "blockchain_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "bridge_events")
  |> filter(fn: (r) => r["source_chain_id"] == "1" and r["dest_chain_id"] == "137")
  |> filter(fn: (r) => r["_field"] == "amount")
  |> sum()
```

### Advanced Query Examples

#### Gas Price Analysis Across Chains
```flux
// Compare average gas prices across EVM chains
from(bucket: "blockchain_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "transactions")
  |> filter(fn: (r) => r["_field"] == "gas_price")
  |> filter(fn: (r) => r["chain_id"] == "1" or r["chain_id"] == "137" or r["chain_id"] == "8453")
  |> group(columns: ["chain_name"])
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> yield(name: "avg_gas_price")
```

#### Top Active Contracts Per Chain
```flux
// Find most active contracts on each chain
from(bucket: "blockchain_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "events")
  |> group(columns: ["chain_name", "contract_address"])
  |> count(column: "_value")
  |> group(columns: ["chain_name"])
  |> top(n: 10, columns: ["_value"])
```

#### DEX Volume Comparison
```flux
// Compare DEX trading volumes across chains
from(bucket: "blockchain_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "dex_swaps")
  |> filter(fn: (r) => r["_field"] == "usd_value")
  |> group(columns: ["chain_name", "dex_name"])
  |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)
  |> pivot(rowKey:["_time"], columnKey: ["chain_name"], valueColumn: "_value")
```

#### Chain Performance Metrics
```flux
// Real-time chain performance dashboard
from(bucket: "blockchain_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "blocks")
  |> filter(fn: (r) => r["_field"] == "block_time" or r["_field"] == "gas_utilization")
  |> group(columns: ["chain_name", "_field"])
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
```

#### Multi-Chain Token Transfer Analysis
```flux
// Analyze USDC transfers across all chains
from(bucket: "blockchain_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "token_transfers")
  |> filter(fn: (r) => r["token_symbol"] == "USDC")
  |> filter(fn: (r) => r["_field"] == "amount")
  |> group(columns: ["chain_name"])
  |> sum()
  |> sort(columns: ["_value"], desc: true)
```

#### Cross-Chain Address Activity
```flux
// Track address activity across multiple chains
address = "0x742d35Cc1cCf..."  // Example address

from(bucket: "blockchain_data")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "transactions")
  |> filter(fn: (r) => r["from_address"] == address or r["to_address"] == address)
  |> group(columns: ["chain_name"])
  |> count(column: "hash")
  |> yield(name: "transactions_per_chain")
```

## Performance Considerations

### Indexing Strategy
- Automatic time-based indexing for all measurements
- Chain ID tags are indexed for fast filtering
- Address tags have high cardinality (100K+ unique values expected)
- Contract addresses have medium cardinality (10K+ unique values)

### Retention Policies by Data Type
```flux
// Real-time monitoring data - 30 days
CREATE RETENTION POLICY "realtime" ON "multichain_analytics" 
DURATION 30d REPLICATION 1

// Raw transaction data - 1 year
CREATE RETENTION POLICY "transactions" ON "multichain_analytics" 
DURATION 365d REPLICATION 1

// Aggregated analytics - 5 years  
CREATE RETENTION POLICY "analytics" ON "multichain_analytics"
DURATION 1825d REPLICATION 1 DEFAULT

// Cross-chain metrics - 2 years
CREATE RETENTION POLICY "crosschain" ON "multichain_analytics"
DURATION 730d REPLICATION 1
```

### Cardinality Management
- Chain tags: Low cardinality (6 chains currently)
- Address tags: High cardinality, implement sampling for less active addresses
- Contract tags: Medium cardinality, focus on verified/popular contracts
- Token tags: Medium cardinality, prioritize high-volume tokens

## Multi-Chain Analytics Capabilities

This schema enables:
1. **Cross-chain transaction volume comparison**
2. **Multi-chain DeFi activity tracking**
3. **Bridge usage analytics**
4. **Chain performance benchmarking**
5. **Token movement across ecosystems**
6. **Multi-chain address behavior analysis**
7. **Ecosystem growth comparison**
8. **Gas fee analysis across chains**

## Migration from Single-Chain

For existing GLQ Chain data:
1. Add chain identification tags to existing data points
2. Maintain backward compatibility with single-chain queries
3. Gradually migrate to multi-chain client usage
4. Implement chain-specific retention policies as needed