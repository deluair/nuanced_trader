#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Adaptive Momentum Strategy
-------------------------

This module provides an adaptive momentum trading strategy that combines
multiple indicators and adapts to market conditions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time

from src.data.data_provider import DataProvider
from src.strategies.base_strategy import BaseStrategy


class AdaptiveMomentumStrategy(BaseStrategy):
    """
    Adaptive Momentum Strategy.
    
    This strategy combines multiple indicators (trend, momentum, volatility)
    and adapts to current market conditions to generate signals.
    """
    
    def _initialize_strategy(self) -> None:
        """Initialize strategy parameters."""
        # Trend Parameters
        self.sma_short = self.get_parameter('sma_short', 20)
        self.sma_long = self.get_parameter('sma_long', 50)
        self.ema_short = self.get_parameter('ema_short', 9)
        self.ema_long = self.get_parameter('ema_long', 21)
        
        # Momentum Parameters
        self.rsi_period = self.get_parameter('rsi_period', 14)
        self.rsi_overbought = self.get_parameter('rsi_overbought', 70)
        self.rsi_oversold = self.get_parameter('rsi_oversold', 30)
        
        # Bollinger Bands Parameters
        self.bollinger_period = self.get_parameter('bollinger_period', 20)
        self.bollinger_std = self.get_parameter('bollinger_std', 2)
        
        # Market Regime Parameters
        self.regime_lookback = self.get_parameter('regime_lookback', 50)
        self.volatility_lookback = self.get_parameter('volatility_lookback', 20)
        
        # State variables
        self.market_regimes = {}  # Stores market regime for each pair
        self.active_positions = {}  # Tracks active positions
        
        self.logger.info("Initialized Adaptive Momentum Strategy")
    
    def generate_signals(self) -> List[Dict[str, Any]]:
        """
        Generate trading signals for all pairs.
        
        Returns:
            List of trading signals
        """
        signals = []
        
        # Process each trading pair
        for pair in self.data_provider.trading_pairs:
            try:
                # Get OHLCV data
                df = self.data_provider.get_ohlcv(pair)
                
                if df.empty:
                    self.logger.warning(f"No data available for {pair}")
                    continue
                
                # Determine market regime
                market_regime = self._determine_market_regime(df)
                self.market_regimes[pair] = market_regime
                
                # Generate signal based on market regime
                signal = self._generate_signal_for_pair(pair, df, market_regime)
                
                if signal:
                    signals.append(signal)
                
            except Exception as e:
                self.logger.error(f"Error generating signal for {pair}: {str(e)}")
        
        return signals
    
    def _determine_market_regime(self, df: pd.DataFrame) -> str:
        """
        Determine the current market regime.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Market regime: 'trending', 'ranging', 'volatile'
        """
        # Check if we have enough data
        if len(df) < self.regime_lookback:
            return 'unknown'
        
        # Get recent data
        recent_data = df.tail(self.regime_lookback)
        
        # Calculate ADX for trend strength
        adx_values = recent_data['adx'].values
        adx_current = adx_values[-1]
        
        # Calculate Bollinger Width for volatility
        bb_width = recent_data['bollinger_width'].values
        bb_width_current = bb_width[-1]
        bb_width_avg = np.mean(bb_width)
        
        # Calculate recent volatility
        returns = recent_data['close'].pct_change().dropna()
        recent_volatility = returns.tail(self.volatility_lookback).std() * 100
        
        # Determine market regime
        if adx_current > 25:
            # Strong trend detected
            regime = 'trending'
        elif recent_volatility > 2.5 or bb_width_current > bb_width_avg * 1.5:
            # High volatility detected
            regime = 'volatile'
        else:
            # Range-bound market
            regime = 'ranging'
        
        self.logger.debug(f"Market regime: {regime} (ADX: {adx_current:.1f}, Volatility: {recent_volatility:.2f}%, BB Width: {bb_width_current:.4f})")
        
        return regime
    
    def _generate_signal_for_pair(self, pair: str, df: pd.DataFrame, market_regime: str) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal for a specific pair based on market regime.
        
        Args:
            pair: Trading pair
            df: OHLCV DataFrame
            market_regime: Current market regime
            
        Returns:
            Trading signal or None
        """
        if df.empty or len(df) < 50:  # Need enough data for indicators
            return None
        
        # Get current price and other data
        current_price = df['close'].iloc[-1]
        current_timestamp = int(time.time() * 1000)
        
        # Determine which strategy to use based on market regime
        if market_regime == 'trending':
            signal_data = self._trending_market_strategy(pair, df)
        elif market_regime == 'ranging':
            signal_data = self._ranging_market_strategy(pair, df)
        elif market_regime == 'volatile':
            signal_data = self._volatile_market_strategy(pair, df)
        else:
            # Default to trending if regime unknown
            signal_data = self._trending_market_strategy(pair, df)
        
        if not signal_data:
            return None
        
        action, reason, confidence = signal_data
        
        # Determine position size - this is simplified
        # In a real strategy, this would be handled by the risk manager
        stake_amount = 100  # Fixed amount per trade
        amount = stake_amount / current_price
        
        # Calculate stop loss and take profit levels
        stop_loss, take_profit = self._calculate_exit_levels(df, action, market_regime)
        
        # Create signal
        signal = {
            'pair': pair,
            'action': action,
            'amount': amount,
            'reason': f"{market_regime}_{reason}",
            'timeframe': self.data_provider.timeframe,
            'timestamp': current_timestamp,
            'confidence': confidence,
            'market_regime': market_regime
        }
        
        # Add stop loss and take profit if available
        if stop_loss:
            signal['stop_loss'] = stop_loss
        
        if take_profit:
            signal['take_profit'] = take_profit
        
        return signal
    
    def _trending_market_strategy(self, pair: str, df: pd.DataFrame) -> Optional[Tuple[str, str, float]]:
        """
        Strategy for trending markets - focuses on trend following.
        
        Args:
            pair: Trading pair
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (action, reason, confidence) or None
        """
        # Check for bullish trend
        bullish_trend = (
            (df['ema_short'].iloc[-1] > df['ema_long'].iloc[-1]) and
            (df['sma_short'].iloc[-1] > df['sma_long'].iloc[-1]) and
            (df['close'].iloc[-1] > df['sma_short'].iloc[-1])
        )
        
        # Check for bearish trend
        bearish_trend = (
            (df['ema_short'].iloc[-1] < df['ema_long'].iloc[-1]) and
            (df['sma_short'].iloc[-1] < df['sma_long'].iloc[-1]) and
            (df['close'].iloc[-1] < df['sma_short'].iloc[-1])
        )
        
        # Check for recent EMA crossover
        bullish_crossover = (
            (df['ema_short'].iloc[-2] <= df['ema_long'].iloc[-2]) and
            (df['ema_short'].iloc[-1] > df['ema_long'].iloc[-1])
        )
        
        bearish_crossover = (
            (df['ema_short'].iloc[-2] >= df['ema_long'].iloc[-2]) and
            (df['ema_short'].iloc[-1] < df['ema_long'].iloc[-1])
        )
        
        # MACD confirmation
        macd_bullish = (
            (df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]) and
            (df['macd_histogram'].iloc[-1] > 0) and
            (df['macd_histogram'].iloc[-1] > df['macd_histogram'].iloc[-2])
        )
        
        macd_bearish = (
            (df['macd'].iloc[-1] < df['macd_signal'].iloc[-1]) and
            (df['macd_histogram'].iloc[-1] < 0) and
            (df['macd_histogram'].iloc[-1] < df['macd_histogram'].iloc[-2])
        )
        
        # Final signal logic for trending market
        if bullish_crossover and macd_bullish:
            confidence = 0.8
            return 'buy', 'ema_crossover_with_macd', confidence
        elif bullish_trend and macd_bullish and df['adx'].iloc[-1] > 25:
            confidence = 0.7
            return 'buy', 'strong_trend_continuation', confidence
        elif bearish_crossover and macd_bearish:
            confidence = 0.8
            return 'sell', 'ema_crossover_with_macd', confidence
        elif bearish_trend and macd_bearish and df['adx'].iloc[-1] > 25:
            confidence = 0.7
            return 'sell', 'strong_trend_continuation', confidence
        
        return None
    
    def _ranging_market_strategy(self, pair: str, df: pd.DataFrame) -> Optional[Tuple[str, str, float]]:
        """
        Strategy for ranging markets - focuses on mean reversion.
        
        Args:
            pair: Trading pair
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (action, reason, confidence) or None
        """
        # Check if price is near Bollinger Bands
        near_upper_band = df['close'].iloc[-1] > df['bollinger_upper'].iloc[-1] * 0.98
        near_lower_band = df['close'].iloc[-1] < df['bollinger_lower'].iloc[-1] * 1.02
        
        # RSI conditions
        rsi_oversold = df['rsi_14'].iloc[-1] < self.rsi_oversold
        rsi_overbought = df['rsi_14'].iloc[-1] > self.rsi_overbought
        
        # Stochastic conditions
        stoch_oversold = df['stoch_k'].iloc[-1] < 20 and df['stoch_d'].iloc[-1] < 20
        stoch_overbought = df['stoch_k'].iloc[-1] > 80 and df['stoch_d'].iloc[-1] > 80
        
        # Final signal logic for ranging market
        if near_lower_band and rsi_oversold and stoch_oversold:
            confidence = 0.75
            return 'buy', 'oversold_bounce', confidence
        elif near_upper_band and rsi_overbought and stoch_overbought:
            confidence = 0.75
            return 'sell', 'overbought_reversal', confidence
        
        return None
    
    def _volatile_market_strategy(self, pair: str, df: pd.DataFrame) -> Optional[Tuple[str, str, float]]:
        """
        Strategy for volatile markets - focuses on breakouts and quick trades.
        
        Args:
            pair: Trading pair
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (action, reason, confidence) or None
        """
        # Calculate recent volatility
        returns = df['close'].pct_change().dropna()
        volatility = returns.tail(self.volatility_lookback).std() * 100
        
        # Ichimoku Cloud signals
        above_cloud = (
            df['close'].iloc[-1] > df['ichimoku_a'].iloc[-1] and
            df['close'].iloc[-1] > df['ichimoku_b'].iloc[-1]
        )
        
        below_cloud = (
            df['close'].iloc[-1] < df['ichimoku_a'].iloc[-1] and
            df['close'].iloc[-1] < df['ichimoku_b'].iloc[-1]
        )
        
        # Volume confirmation
        volume_surge = df['volume'].iloc[-1] > df['volume'].rolling(10).mean().iloc[-1] * 1.5
        
        # ADX filter for strong moves
        strong_adx = df['adx'].iloc[-1] > 30
        
        # Breakout detection
        upper_breakout = (
            df['close'].iloc[-1] > df['bollinger_upper'].iloc[-1] and
            df['close'].iloc[-2] <= df['bollinger_upper'].iloc[-2] and
            volume_surge
        )
        
        lower_breakout = (
            df['close'].iloc[-1] < df['bollinger_lower'].iloc[-1] and
            df['close'].iloc[-2] >= df['bollinger_lower'].iloc[-2] and
            volume_surge
        )
        
        # Final signal logic for volatile market
        if upper_breakout and above_cloud and strong_adx:
            confidence = 0.6  # Lower confidence due to volatility
            return 'buy', 'volatility_breakout', confidence
        elif lower_breakout and below_cloud and strong_adx:
            confidence = 0.6  # Lower confidence due to volatility
            return 'sell', 'volatility_breakdown', confidence
        
        return None
    
    def _calculate_exit_levels(self, df: pd.DataFrame, action: str, 
                             market_regime: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate stop loss and take profit levels based on market regime.
        
        Args:
            df: OHLCV DataFrame
            action: 'buy' or 'sell'
            market_regime: Current market regime
            
        Returns:
            Tuple of (stop_loss, take_profit) prices
        """
        current_price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        # Adjust ATR multipliers based on market regime
        if market_regime == 'trending':
            sl_multiplier = 2.0
            tp_multiplier = 3.0
        elif market_regime == 'ranging':
            sl_multiplier = 1.5
            tp_multiplier = 2.0
        else:  # volatile
            sl_multiplier = 3.0
            tp_multiplier = 4.0
        
        if action == 'buy':
            stop_loss = current_price - (atr * sl_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
        else:  # sell
            stop_loss = current_price + (atr * sl_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
        
        # For ranging market, use scaled take profits
        if market_regime == 'ranging':
            if action == 'buy':
                take_profit = [
                    current_price + (atr * 1.0),
                    current_price + (atr * 2.0),
                    current_price + (atr * 3.0)
                ]
            else:  # sell
                take_profit = [
                    current_price - (atr * 1.0),
                    current_price - (atr * 2.0),
                    current_price - (atr * 3.0)
                ]
        
        return round(stop_loss, 8), take_profit 