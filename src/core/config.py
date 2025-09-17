"""
Configuration Manager for Blockchain Analytics System
Loads and validates configuration from YAML files and environment variables.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the blockchain analytics system."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load environment variables
        load_dotenv()
        
        # Set default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = {}
        
        # Load configuration
        self._load_config()
        self._validate_config()
        
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                self._config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
            
    def _validate_config(self):
        """Validate configuration and apply environment variable overrides."""
        # Blockchain configuration
        if 'blockchain' not in self._config:
            raise ValueError("Missing 'blockchain' configuration section")
            
        # InfluxDB configuration
        if 'influxdb' not in self._config:
            raise ValueError("Missing 'influxdb' configuration section")
            
        # Override with environment variables
        influx_token = os.getenv('INFLUX_TOKEN')
        if influx_token:
            self._config['influxdb']['token'] = influx_token
        else:
            logger.warning("INFLUX_TOKEN environment variable not set")
            
        influx_org = os.getenv('INFLUX_ORG')
        if influx_org:
            self._config['influxdb']['org'] = influx_org
            
        influx_bucket = os.getenv('INFLUX_BUCKET')
        if influx_bucket:
            self._config['influxdb']['bucket'] = influx_bucket
            
        # Performance settings from environment
        max_workers = os.getenv('MAX_WORKERS')
        if max_workers:
            self._config['processing']['max_workers'] = int(max_workers)
            
        debug_mode = os.getenv('DEBUG_MODE', 'false').lower()
        if debug_mode == 'true':
            self._config['logging']['level'] = 'DEBUG'
    
    # Blockchain configuration properties
    @property
    def blockchain_rpc_url(self) -> str:
        return self._config['blockchain']['rpc_url']
    
    @property
    def blockchain_ws_url(self) -> Optional[str]:
        return self._config['blockchain'].get('ws_url')
    
    @property
    def blockchain_chain_id(self) -> int:
        return self._config['blockchain']['chain_id']
    
    @property
    def blockchain_network_type(self) -> str:
        return self._config['blockchain']['network_type']
    
    # InfluxDB configuration properties
    @property
    def influxdb_url(self) -> str:
        return self._config['influxdb']['url']
    
    @property
    def influxdb_token(self) -> str:
        return self._config['influxdb'].get('token', '')
    
    @property
    def influxdb_org(self) -> str:
        return self._config['influxdb']['org']
    
    @property
    def influxdb_bucket(self) -> str:
        return self._config['influxdb']['bucket']
    
    # Processing configuration properties
    @property
    def processing_batch_size(self) -> int:
        return self._config['processing']['batch_size']
    
    @property
    def processing_max_workers(self) -> int:
        return self._config['processing']['max_workers']
    
    @property
    def processing_start_block(self) -> int:
        return self._config['processing']['start_block']
    
    @property
    def processing_end_block(self) -> str:
        return self._config['processing']['end_block']
    
    @property
    def real_time_enabled(self) -> bool:
        return self._config['processing']['real_time_enabled']
    
    @property
    def poll_interval(self) -> int:
        return self._config['processing']['poll_interval']
    
    @property
    def confirmation_blocks(self) -> int:
        return self._config['processing']['confirmation_blocks']
    
    # Analytics configuration properties
    @property
    def analytics_config(self) -> Dict[str, Any]:
        return self._config.get('analytics', {})
    
    def is_analytics_enabled(self, feature: str) -> bool:
        """Check if a specific analytics feature is enabled."""
        return self.analytics_config.get(feature, False)
    
    # Contract configuration
    @property
    def known_contracts(self) -> Dict[str, Any]:
        return self._config.get('contracts', {})
    
    # Logging configuration
    @property
    def logging_level(self) -> str:
        return self._config['logging']['level']
    
    @property
    def logging_file(self) -> str:
        return self._config['logging']['file']
    
    @property
    def logging_format(self) -> str:
        return self._config['logging']['format']
    
    # Performance configuration
    @property
    def max_connections(self) -> int:
        return self._config['performance']['max_connections']
    
    @property
    def connection_timeout(self) -> int:
        return self._config['performance']['connection_timeout']
    
    # Monitoring configuration
    @property
    def monitoring_enabled(self) -> bool:
        return self._config['monitoring']['enable_metrics']
    
    @property
    def metrics_port(self) -> int:
        return self._config['monitoring']['metrics_port']
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key with dot notation support."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def update(self, key: str, value: Any):
        """Update configuration value."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config()
        self._validate_config()
        logger.info("Configuration reloaded")
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """Support dictionary-style access."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """Support dictionary-style assignment."""
        self.update(key, value)