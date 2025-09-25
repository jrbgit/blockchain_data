# InfluxDB Schema Design for GraphLinq Chain Analytics

## Overview
This document defines the InfluxDB measurements, tags, and fields for storing comprehensive blockchain analytics data.

## Measurements Structure

### 1. `blocks` - Block-level Data
**Tags:**
- `chain_id`: 614 (static for GLQ chain)
- `network`: "mainnet"
- `miner`: Block miner address

**Fields:**
- `block_number`: Block height (integer)
- `timestamp`: Block timestamp (timestamp)
- `gas_limit`: Block gas limit (integer)
- `gas_used`: Gas used in block (integer)
- `transaction_count`: Number of transactions (integer)
- `size`: Block size in bytes (integer)
- `difficulty`: Block difficulty (string/big number)
- `total_difficulty`: Cumulative difficulty (string/big number)
- `base_fee_per_gas`: EIP-1559 base fee (integer)
- `block_time`: Time since last block in seconds (float)
- `gas_utilization`: gas_used/gas_limit ratio (float)

### 2. `transactions` - Transaction-level Data
**Tags:**
- `chain_id`: 614
- `from_address`: Sender address
- `to_address`: Receiver address (null for contract creation)
- `transaction_type`: "transfer", "contract_call", "contract_creation", "token_transfer"
- `status`: "success", "failed", "pending"

**Fields:**
- `block_number`: Block containing transaction (integer)
- `transaction_index`: Position in block (integer)
- `hash`: Transaction hash (string)
- `nonce`: Transaction nonce (integer)
- `value`: ETH value transferred (string/big number)
- `gas_limit`: Gas limit set (integer)
- `gas_used`: Actual gas used (integer)
- `gas_price`: Gas price paid (integer)
- `effective_gas_price`: Actual gas price after EIP-1559 (integer)
- `transaction_fee`: Total fee paid (string/big number)
- `input_data_size`: Size of input data (integer)

### 3. `events` - Smart Contract Events/Logs
**Tags:**
- `chain_id`: 614
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

### 4. `token_transfers` - ERC-20/721/1155 Transfers
**Tags:**
- `chain_id`: 614
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

### 5. `dex_swaps` - DEX Swap Transactions
**Tags:**
- `chain_id`: 614
- `dex_name`: DEX protocol name ("uniswap", "sushiswap", etc.)
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

### 6. `liquidity_events` - LP Token Events
**Tags:**
- `chain_id`: 614
- `pool_address`: Liquidity pool address
- `token0_address`: First token address
- `token1_address`: Second token address
- `provider_address`: LP provider address
- `event_type`: "mint", "burn"

**Fields:**
- `block_number`: Block number (integer)
- `transaction_hash`: Transaction hash (string)
- `token0_amount`: Amount of token0 (string)
- `token1_amount`: Amount of token1 (string)
- `lp_token_amount`: LP tokens minted/burned (string)
- `total_supply`: Total LP token supply after event (string)

### 7. `contracts` - Smart Contract Data
**Tags:**
- `chain_id`: 614
- `contract_address`: Contract address
- `contract_type`: "token", "dex", "defi", "nft", "other"
- `deployer_address`: Contract deployer

**Fields:**
- `deployment_block`: Block when deployed (integer)
- `deployment_transaction`: Deployment tx hash (string)
- `bytecode_size`: Size of contract bytecode (integer)
- `is_verified`: Whether source is verified (boolean)
- `interaction_count`: Number of interactions (integer)
- `gas_consumed_total`: Total gas used by contract (integer)
- `unique_users`: Number of unique interacting addresses (integer)

### 8. `addresses` - Address Analytics
**Tags:**
- `chain_id`: 614
- `address`: Ethereum address
- `address_type`: "eoa", "contract", "multisig"
- `cluster_id`: Wallet clustering identifier

**Fields:**
- `first_activity_block`: First transaction block (integer)
- `last_activity_block`: Most recent transaction block (integer)
- `transaction_count`: Total transactions (integer)
- `balance`: Current ETH balance (string)
- `total_received`: Total ETH received (string)
- `total_sent`: Total ETH sent (string)
- `gas_consumed`: Total gas consumed (integer)
- `unique_contracts`: Number of unique contracts interacted with (integer)

### 9. `network_metrics` - Network-wide Analytics
**Tags:**
- `chain_id`: 614
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
- `total_value_transferred`: Total ETH transferred (string)

### 10. `defi_metrics` - DeFi Protocol Analytics
**Tags:**
- `chain_id`: 614
- `protocol`: Protocol name
- `metric_type`: "tvl", "volume", "users"

**Fields:**
- `block_number`: Reference block (integer)
- `tvl_usd`: Total Value Locked in USD (float)
- `volume_24h`: 24h trading volume (string)
- `unique_users_24h`: Unique users in 24h (integer)
- `total_fees`: Total fees collected (string)

## Retention Policies

```flux
// Raw blockchain data - 1 year retention
CREATE RETENTION POLICY "blockchain_raw" ON "glq_analytics" 
DURATION 365d REPLICATION 1 DEFAULT

// Aggregated analytics - 5 year retention  
CREATE RETENTION POLICY "analytics_long" ON "glq_analytics"
DURATION 1825d REPLICATION 1

// Real-time monitoring - 30 day retention
CREATE RETENTION POLICY "realtime_monitoring" ON "glq_analytics"
DURATION 30d REPLICATION 1
```

## Indexes and Performance

### Common Query Patterns:
1. Time-based queries (automatic time indexing)
2. Address-based queries (index on address tags)
3. Contract interaction queries (index on contract_address)
4. Token transfer queries (index on token_address)

### Suggested Tag Cardinality Limits:
- `address` tags: High cardinality, expect 100K+ unique values
- `contract_address`: Medium cardinality, expect 10K+ unique values
- `token_address`: Low-medium cardinality, expect 1K+ unique values
- `chain_id`: Static, single value (614)

This schema supports:
- Real-time blockchain monitoring
- Historical data analysis
- Cross-contract relationship tracking
- DeFi protocol analytics
- Wallet behavior analysis
- Network performance metrics