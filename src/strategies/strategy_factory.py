#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Strategy Factory
--------------

This module provides a factory for creating trading strategies.
"""

from typing import Dict, Any, Type
from loguru import logger

from src.data.data_provider import DataProvider
from src.strategies.base_strategy import BaseStrategy
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.ml_strategy import MachineLearningStrategy
from src.strategies.adaptive_momentum import AdaptiveMomentumStrategy


class StrategyFactory:
    """Factory for creating trading strategies."""
    
    # Registry of available strategies
    _strategies: Dict[str, Type[BaseStrategy]] = {
        'trend_following': TrendFollowingStrategy,
        'mean_reversion': MeanReversionStrategy,
        'momentum': MomentumStrategy,
        'machine_learning': MachineLearningStrategy,
        'adaptive_momentum': AdaptiveMomentumStrategy,
    }
    
    @classmethod
    def create_strategy(cls, strategy_name: str, parameters: Dict[str, Any],
                       data_provider: DataProvider) -> BaseStrategy:
        """
        Create a strategy instance.
        
        Args:
            strategy_name: Name of the strategy
            parameters: Strategy parameters
            data_provider: Data provider instance
        
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If strategy is not found
        """
        strategy_name = strategy_name.lower()
        
        if strategy_name not in cls._strategies:
            logger.error(f"Strategy '{strategy_name}' not found")
            available_strategies = ", ".join(cls._strategies.keys())
            raise ValueError(f"Strategy '{strategy_name}' not found. Available strategies: {available_strategies}")
        
        strategy_class = cls._strategies[strategy_name]
        logger.info(f"Creating strategy: {strategy_name}")
        
        return strategy_class(parameters, data_provider)
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """
        Register a new strategy.
        
        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        cls._strategies[name.lower()] = strategy_class
        logger.info(f"Registered new strategy: {name}")
    
    @classmethod
    def get_available_strategies(cls) -> Dict[str, Type[BaseStrategy]]:
        """
        Get all available strategies.
        
        Returns:
            Dict of strategy names and classes
        """
        return cls._strategies.copy() 