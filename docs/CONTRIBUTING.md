# Contributing to GLQ Chain Analytics Platform

Thank you for your interest in contributing to the GLQ Chain Analytics Platform! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git fork <repository-url>
   git clone <your-fork-url>
   cd blockchain_data
   ```

2. **Install Development Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

3. **Setup Pre-commit Hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Configure your environment variables
   ```

## 🏗️ Project Structure

Understanding the codebase structure will help you contribute effectively:

### Core Components
- `src/core/` - Core infrastructure (blockchain client, database, config)
- `src/processors/` - Data processing modules (historical, real-time, monitoring)
- `src/analytics/` - Advanced analytics modules (token, DEX, DeFi)
- `config/` - Configuration files and schemas
- `tests/` - Unit and integration tests

### Key Files
- `config/config.yaml` - Main configuration file
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Docker services configuration
- `test_setup.py` - System health check

## 🎯 Contributing Areas

### 1. Analytics Modules
**What**: Extend analytics capabilities for specific protocols or use cases
**Examples**:
- New DeFi protocol parsers (MakerDAO, Curve, etc.)
- NFT marketplace analytics
- Cross-chain bridge tracking
- MEV detection algorithms

**Getting Started**:
- Review existing modules in `src/analytics/`
- Follow the pattern established in `token_analytics.py`
- Implement proper event signature detection
- Include comprehensive tests

### 2. Data Processing Improvements
**What**: Optimize processing speed, memory usage, or reliability
**Examples**:
- Parallel processing optimizations
- Memory usage improvements
- Error handling enhancements
- Resume/checkpoint mechanisms

**Areas to Focus**:
- `src/processors/historical_clean.py` - Historical data processing
- `src/processors/realtime_monitor.py` - Real-time monitoring
- `src/core/blockchain_client.py` - RPC client optimizations

### 3. Monitoring & Visualization
**What**: Improve monitoring capabilities and data visualization
**Examples**:
- Enhanced web dashboard features
- Grafana dashboard templates
- Alert mechanisms
- Performance metrics

**Components**:
- `src/processors/monitoring_service.py` - Web service
- Dashboard HTML/CSS/JavaScript
- API endpoint extensions

### 4. Testing & Quality
**What**: Improve test coverage and code quality
**Examples**:
- Unit tests for analytics modules
- Integration tests for processors
- Performance benchmarks
- Code quality improvements

## 📋 Development Guidelines

### Code Style

1. **Python Style**
   - Follow PEP 8 guidelines
   - Use type hints for function parameters and returns
   - Maximum line length: 100 characters
   - Use descriptive variable and function names

2. **Documentation**
   ```python
   def process_block(self, block_data: Dict[str, Any]) -> BlockResult:
       """Process a single blockchain block.
       
       Args:
           block_data: Raw block data from blockchain RPC
           
       Returns:
           BlockResult object with processed data
           
       Raises:
           ProcessingError: If block data is invalid
       """
   ```

3. **Error Handling**
   - Use specific exception types
   - Log errors with appropriate severity
   - Provide meaningful error messages
   - Implement graceful degradation where possible

4. **Configuration**
   - Use the configuration system in `src/core/config.py`
   - Add new settings to `config/config.yaml`
   - Provide sensible defaults
   - Document configuration options

### Testing Requirements

1. **Unit Tests**
   ```python
   import pytest
   from src.analytics.token_analytics import TokenAnalytics
   
   def test_token_transfer_parsing():
       """Test token transfer event parsing."""
       # Test implementation
       pass
   ```

2. **Integration Tests**
   - Test end-to-end workflows
   - Test database interactions
   - Test blockchain client functionality

3. **Performance Tests**
   - Benchmark processing speeds
   - Memory usage profiling
   - Database query performance

### Database Schema Changes

1. **InfluxDB Schema Updates**
   - Document schema changes in `docs/schema.md`
   - Provide migration scripts if needed
   - Test with sample data
   - Consider backward compatibility

2. **New Measurements**
   ```python
   # Example: Adding new measurement
   point = Point("new_measurement") \
       .tag("protocol", protocol_name) \
       .tag("event_type", event_type) \
       .field("amount", amount) \
       .field("block_number", block_number) \
       .time(timestamp)
   ```

## 🔄 Pull Request Process

### 1. Before Creating a PR

- [ ] Create issue describing the feature/bug
- [ ] Fork the repository
- [ ] Create feature branch: `git checkout -b feature/your-feature-name`
- [ ] Implement changes with tests
- [ ] Update documentation
- [ ] Run tests locally
- [ ] Test with real blockchain data

### 2. PR Checklist

- [ ] **Clear Description**: Explain what the PR does and why
- [ ] **Issue Reference**: Link to related issue(s)
- [ ] **Tests**: Include appropriate tests
- [ ] **Documentation**: Update relevant documentation
- [ ] **Configuration**: Update config files if needed
- [ ] **Performance**: Consider performance implications
- [ ] **Breaking Changes**: Document any breaking changes

### 3. PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Performance improvement
- [ ] Documentation update
- [ ] Configuration change

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Tested with real blockchain data
- [ ] Performance impact assessed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Configuration updated if needed
```

## 🧪 Testing Your Changes

### 1. Unit Tests
```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/test_analytics.py

# Run with coverage
pytest --cov=src/
```

### 2. Integration Testing
```bash
# Test system setup
python test_setup.py

# Test with small dataset
python -m pytest tests/integration/

# Test analytics modules
python src/analytics/token_analytics.py
```

### 3. Performance Testing
```bash
# Test historical processing with limited blocks
# Modify historical_clean.py to use max_blocks=1000

# Monitor resource usage
htop  # or Task Manager on Windows
```

## 📚 Development Resources

### Architecture Documentation
- [System Architecture](docs/architecture.md)
- [Database Schema](docs/schema.md)
- [API Reference](docs/api.md)

### Code Examples
- Review existing analytics modules in `src/analytics/`
- Check processor implementations in `src/processors/`
- Study configuration patterns in `src/core/config.py`

### Tools & Libraries
- **Web3 Libraries**: For blockchain interaction
- **InfluxDB**: Time-series database operations
- **AsyncIO**: Asynchronous programming patterns
- **Rich**: Terminal UI and progress display
- **FastAPI/aiohttp**: Web service development

## 🚨 Common Pitfalls

### 1. Memory Management
- Process data in batches, don't load everything into memory
- Use generators and iterators for large datasets
- Monitor memory usage during development

### 2. Blockchain Data Handling
- Always handle `None` values (e.g., contract creation transactions)
- Convert hex values to integers properly
- Validate data before processing
- Handle network timeouts and failures

### 3. Database Operations
- Use batch writes for better performance
- Implement proper error handling
- Consider database constraints and indexing
- Test queries for performance

### 4. Configuration
- Don't hardcode values, use configuration
- Provide environment variable overrides
- Document all configuration options
- Use sensible defaults

## 🆘 Getting Help

### Development Support
- **GitHub Issues**: Create an issue for questions or problems
- **Code Review**: Request review from maintainers
- **Documentation**: Check existing documentation first

### Testing Environment
- Use the test blockchain data for development
- Start with small datasets before full processing
- Monitor system resources during testing

## 🏷️ Issue Labels

When creating issues or PRs, use appropriate labels:

- `enhancement` - New features
- `bug` - Bug fixes
- `performance` - Performance improvements
- `documentation` - Documentation updates
- `analytics` - Analytics module changes
- `monitoring` - Monitoring/dashboard changes
- `core` - Core infrastructure changes
- `good first issue` - Good for newcomers
- `help wanted` - Community help requested

## 🎉 Recognition

Contributors will be recognized in:
- Project README
- Release notes
- Contributor documentation

Thank you for contributing to the GLQ Chain Analytics Platform!

---

## Quick Start for Contributors

```bash
# 1. Fork and clone
git clone <your-fork>
cd blockchain_data

# 2. Setup environment
pip install -r requirements.txt
cp .env.example .env

# 3. Test setup
python test_setup.py

# 4. Create feature branch
git checkout -b feature/my-feature

# 5. Make changes and test
python -m pytest

# 6. Commit and push
git commit -m "Add feature: description"
git push origin feature/my-feature

# 7. Create pull request
```

Happy coding! 🚀