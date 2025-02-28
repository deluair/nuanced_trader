#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Loader
-------------------

This module handles loading and validating configuration files for the trading bot.
"""

import os
import yaml
import logging
from pathlib import Path
from loguru import logger
import json
from typing import Dict, Any, List, Optional


class ConfigLoader:
    """
    Utility class for loading and validating configuration files
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the config loader
        
        Args:
            config_path: Path to the configuration file (default: config.yml in the project root)
        """
        self.logger = logging.getLogger(__name__)
        
        # Set default config path if not provided
        if config_path is None:
            # Try to find the config.yml file
            project_root = self._find_project_root()
            config_path = os.path.join(project_root, 'config.yml')
            
        self.config_path = config_path
        self.config = {}
        
        # Load the configuration
        self.load_config()
        
    def _find_project_root(self) -> str:
        """Find the project root directory"""
        # Start from the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Go up the directory tree until we find a directory containing config.yml or reach the root
        while current_dir and not os.path.isfile(os.path.join(current_dir, 'config.yml')):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # We've reached the root
                break
            current_dir = parent_dir
            
        # If we didn't find the config file, use the current directory
        if not os.path.isfile(os.path.join(current_dir, 'config.yml')):
            return os.path.dirname(os.path.abspath(__file__))
            
        return current_dir
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the YAML file
        
        Returns:
            Dictionary with configuration values
        """
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                
            self.logger.info(f"Loaded configuration from {self.config_path}")
            
            # Validate the configuration
            self._validate_config()
            
            return self.config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
            
    def _validate_config(self):
        """Validate the configuration structure and values"""
        required_sections = ['general', 'exchange', 'trading', 'risk_management']
        
        # Check for required sections
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
                
        # Validate exchange configuration
        exchange_config = self.config['exchange']
        if 'name' not in exchange_config:
            raise ValueError("Exchange name is required in the configuration")
            
        # Validate trading configuration
        trading_config = self.config['trading']
        if 'pairs' not in trading_config or not trading_config['pairs']:
            raise ValueError("At least one trading pair must be specified")
            
        if 'timeframe' not in trading_config:
            raise ValueError("Trading timeframe is required")
            
        if 'strategy' not in trading_config:
            raise ValueError("Trading strategy is required")
            
        # Validate risk management configuration
        risk_config = self.config['risk_management']
        if 'max_risk_per_trade' not in risk_config:
            raise ValueError("Maximum risk per trade is required")
            
    def get_config(self) -> Dict[str, Any]:
        """Get the full configuration"""
        return self.config
        
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get a specific section of the configuration
        
        Args:
            section: Name of the configuration section
            
        Returns:
            Dictionary with section values
        """
        if section in self.config:
            return self.config[section]
        else:
            self.logger.warning(f"Configuration section not found: {section}")
            return {}
            
    def get_value(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific value from the configuration
        
        Args:
            section: Name of the configuration section
            key: Name of the configuration key
            default: Default value to return if the key is not found
            
        Returns:
            Configuration value or default
        """
        section_data = self.get_section(section)
        
        if key in section_data:
            return section_data[key]
        else:
            self.logger.debug(f"Configuration key not found: {section}.{key}, using default: {default}")
            return default
            
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update the configuration with new values
        
        Args:
            updates: Dictionary with updates to apply to the configuration
        """
        # Update the configuration
        self._update_dict(self.config, updates)
        
        # Save the updated configuration
        self.save_config()
        
    def _update_dict(self, target: Dict, updates: Dict) -> None:
        """Recursively update a dictionary"""
        for key, value in updates.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_dict(target[key], value)
            else:
                target[key] = value
                
    def save_config(self) -> None:
        """Save the configuration to the YAML file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                
            self.logger.info(f"Saved configuration to {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            raise
            
    def create_default_config(self) -> None:
        """Create a default configuration file if one doesn't exist"""
        if os.path.exists(self.config_path):
            self.logger.info(f"Configuration file already exists: {self.config_path}")
            return
            
        default_config = {
            'general': {
                'log_level': 'INFO',
                'data_directory': 'data',
                'cache_data': True,
                'max_candles': 1000,
                'backtesting_mode': False
            },
            'exchange': {
                'name': 'binance',
                'api_key': '',
                'api_secret': '',
                'sandbox_mode': True
            },
            'trading': {
                'pairs': ['BTC/USDT', 'ETH/USDT'],
                'timeframe': '1h',
                'strategy': 'AdaptiveMomentumStrategy',
                'strategy_params': {
                    'short_window': 20,
                    'long_window': 50,
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30
                }
            },
            'risk_management': {
                'max_risk_per_trade': 2.0,  # Percentage of account
                'max_total_risk': 15.0,  # Percentage of account
                'stop_loss_atr_multiplier': 2.0,
                'take_profit_atr_multiplier': 3.0,
                'position_sizing': 'risk_based'  # risk_based, percent_based, or fixed
            },
            'notifications': {
                'enabled': True,
                'email': {
                    'enabled': False,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'sender_email': '',
                    'receiver_email': '',
                    'password': ''
                },
                'telegram': {
                    'enabled': False,
                    'bot_token': '',
                    'chat_id': ''
                }
            }
        }
        
        # Save the default configuration
        self.config = default_config
        self.save_config()
        
        self.logger.info(f"Created default configuration at {self.config_path}")


# Singleton instance for easy access
_config_instance = None

def get_config(config_path: str = None) -> ConfigLoader:
    """
    Get the configuration loader instance
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
        
    return _config_instance


def get_strategy_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the strategy-specific configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dict containing strategy configuration
    """
    return config["strategy"]


def get_risk_management_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the risk management configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dict containing risk management configuration
    """
    return config["risk_management"]


def update_config(config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
    """
    Update the configuration with new values and save to file.
    
    Args:
        config: Current configuration dictionary
        new_config: New configuration values to update
        
    Raises:
        yaml.YAMLError: If error saving configuration
    """
    # Update the configuration
    config.update(new_config)
    
    # Validate the new configuration
    validate_config(config)
    
    # Save the updated configuration
    try:
        with open(config["config_path"], 'w') as config_file:
            yaml.safe_dump(config, config_file, default_flow_style=False)
        
        logger.info(f"Configuration updated and saved to {config['config_path']}")
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        raise


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate the configuration.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Check for required sections
    required_sections = ["general", "exchange", "strategy", "risk_management"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
    
    # Validate general settings
    if "log_level" not in config["general"]:
        config["general"]["log_level"] = "INFO"
        logger.warning("Log level not specified, defaulting to INFO")
    
    # Validate exchange settings
    if "trading_pairs" not in config["exchange"] or not config["exchange"]["trading_pairs"]:
        raise ValueError("No trading pairs specified in configuration")
    
    # Validate API keys if live trading is enabled
    if (not config["general"].get("dry_run", True) and 
            (not os.getenv(config["exchange"]["api_key_env"]) or 
             not os.getenv(config["exchange"]["api_secret_env"]))):
        logger.warning("Live trading enabled but API keys not found in environment variables")
    
    logger.info("Configuration validation passed")


def to_json(config: Dict[str, Any]) -> str:
    """
    Convert the configuration to JSON string.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        JSON string representation of the configuration
    """
    return json.dumps(config, indent=2)


@classmethod
def load_from_json(cls, json_str: str) -> 'ConfigLoader':
    """
    Create a ConfigLoader from a JSON string.
    
    Args:
        json_str: JSON string representation of configuration
        
    Returns:
        ConfigLoader instance with configuration from JSON
    """
    config = json.loads(json_str)
    loader = cls()
    loader.config = config
    loader._validate_config()
    return loader 