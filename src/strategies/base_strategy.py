#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base Strategy
------------

This module provides the base class for all trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from loguru import logger

from src.data.data_provider import DataProvider


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, parameters: Dict[str, Any], data_provider: DataProvider):
        """
        Initialize the strategy.
        
        Args:
            parameters: Strategy parameters
            data_provider: Data provider instance
        """
        self.parameters = parameters
        self.data_provider = data_provider
        self.logger = logger.bind(strategy=self.__class__.__name__)
        
        # Initialize strategy
        self._initialize_strategy()
        
        self.logger.info(f"Initialized {self.__class__.__name__} strategy")
    
    def _initialize_strategy(self) -> None:
        """
        Initialize the strategy with parameters.
        Override this method if you need to do strategy-specific initialization.
        """
        pass
    
    @abstractmethod
    def generate_signals(self) -> List[Dict[str, Any]]:
        """
        Generate trading signals for all pairs.
        
        Returns:
            List of trading signals (dictionaries with signal information)
            
        Example signal format:
        {
            'pair': 'BTC/USDT',
            'action': 'buy',  # or 'sell'
            'amount': 0.01,
            'price': 50000.0,  # Optional limit price
            'reason': 'ma_crossover',  # Reason for the signal
            'stop_loss': 48000.0,  # Optional stop loss price
            'take_profit': 52000.0,  # Optional take profit price
            'timeframe': '1h',
            'timestamp': 1234567890,
            'confidence': 0.8,  # Optional confidence score (0.0 to 1.0)
        }
        """
        pass
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate a trading signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['pair', 'action', 'amount']
        
        # Check required fields
        for field in required_fields:
            if field not in signal:
                self.logger.warning(f"Missing required field in signal: {field}")
                return False
        
        # Validate action
        if signal['action'] not in ['buy', 'sell']:
            self.logger.warning(f"Invalid action in signal: {signal['action']}")
            return False
        
        # Validate amount
        if not isinstance(signal['amount'], (int, float)) or signal['amount'] <= 0:
            self.logger.warning(f"Invalid amount in signal: {signal['amount']}")
            return False
        
        # Validate price if present
        if 'price' in signal and (not isinstance(signal['price'], (int, float)) or signal['price'] <= 0):
            self.logger.warning(f"Invalid price in signal: {signal['price']}")
            return False
        
        # Validate stop_loss if present
        if 'stop_loss' in signal and (not isinstance(signal['stop_loss'], (int, float)) or signal['stop_loss'] <= 0):
            self.logger.warning(f"Invalid stop_loss in signal: {signal['stop_loss']}")
            return False
        
        # Validate take_profit if present
        if 'take_profit' in signal and (not isinstance(signal['take_profit'], (int, float)) or signal['take_profit'] <= 0):
            self.logger.warning(f"Invalid take_profit in signal: {signal['take_profit']}")
            return False
        
        return True
    
    def filter_invalid_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out invalid signals.
        
        Args:
            signals: List of trading signals
            
        Returns:
            List of valid trading signals
        """
        valid_signals = [signal for signal in signals if self.validate_signal(signal)]
        
        if len(valid_signals) < len(signals):
            self.logger.warning(f"Filtered out {len(signals) - len(valid_signals)} invalid signals")
        
        return valid_signals
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """
        Get a parameter value.
        
        Args:
            name: Parameter name
            default: Default value if parameter is not found
            
        Returns:
            Parameter value
        """
        return self.parameters.get(name, default)
    
    def set_parameter(self, name: str, value: Any) -> None:
        """
        Set a parameter value.
        
        Args:
            name: Parameter name
            value: Parameter value
        """
        self.parameters[name] = value
        self.logger.debug(f"Set parameter {name} = {value}")
    
    def log_signals(self, signals: List[Dict[str, Any]]) -> None:
        """
        Log trading signals.
        
        Args:
            signals: List of trading signals
        """
        if not signals:
            self.logger.info("No trading signals generated")
            return
        
        self.logger.info(f"Generated {len(signals)} trading signals:")
        
        for i, signal in enumerate(signals):
            self.logger.info(f"Signal {i+1}: {signal['pair']} - {signal['action']} - Amount: {signal['amount']}")
            if 'reason' in signal:
                self.logger.info(f"  Reason: {signal['reason']}")
            if 'price' in signal:
                self.logger.info(f"  Price: {signal['price']}")
            if 'stop_loss' in signal:
                self.logger.info(f"  Stop Loss: {signal['stop_loss']}")
            if 'take_profit' in signal:
                self.logger.info(f"  Take Profit: {signal['take_profit']}")
            if 'confidence' in signal:
                self.logger.info(f"  Confidence: {signal['confidence']}")
    
    def generate_and_filter_signals(self) -> List[Dict[str, Any]]:
        """
        Generate and filter trading signals.
        
        Returns:
            List of valid trading signals
        """
        # Generate signals
        signals = self.generate_signals()
        
        # Filter invalid signals
        filtered_signals = self.filter_invalid_signals(signals)
        
        # Log signals
        self.log_signals(filtered_signals)
        
        return filtered_signals
    
    @property
    def name(self) -> str:
        """
        Get the strategy name.
        
        Returns:
            Strategy name
        """
        return self.__class__.__name__ 