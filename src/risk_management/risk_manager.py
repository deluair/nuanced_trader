#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Risk Manager
-----------

This module provides risk management functionality for the trading bot.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger
from dataclasses import dataclass

from src.data.data_provider import DataProvider
from src.api.exchange_client import ExchangeClient


@dataclass
class PositionSizing:
    """Position sizing calculation result."""
    amount: float
    risk_amount: float
    position_value: float
    risk_percent: float
    method: str


class RiskManager:
    """
    Risk management for the trading bot.
    
    Handles:
    - Position sizing
    - Stop loss calculation
    - Take profit calculation
    - Portfolio risk management
    - Exposure limits
    """
    
    def __init__(self, config: Dict[str, Any], exchange: ExchangeClient, data_provider: DataProvider):
        """
        Initialize the risk manager.
        
        Args:
            config: Risk management configuration
            exchange: Exchange client instance
            data_provider: Data provider instance
        """
        self.config = config
        self.exchange = exchange
        self.data_provider = data_provider
        self.logger = logger.bind(module='RiskManager')
        
        # Load configuration
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 0.02)  # Default 2%
        self.stop_loss_config = self.config.get('stop_loss', {})
        self.take_profit_config = self.config.get('take_profit', {})
        self.position_sizing_config = self.config.get('position_sizing', {})
        
        # Initialize state
        self.open_positions = {}  # Keeps track of open positions
        self.total_exposure = 0.0  # Total exposure across all pairs
        self.pair_exposure = {}  # Exposure per pair
        
        self.logger.info("Risk manager initialized")
    
    def apply_risk_management(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply risk management to trading signals.
        
        Args:
            signals: List of trading signals
            
        Returns:
            List of filtered and adjusted trading signals
        """
        if not signals:
            return []
        
        # Update account information
        try:
            self._update_account_info()
        except Exception as e:
            self.logger.error(f"Error updating account info: {str(e)}")
            return []  # Return empty list if we can't get account info
        
        filtered_signals = []
        
        for signal in signals:
            try:
                # Apply position sizing
                sized_signal = self._apply_position_sizing(signal)
                
                if not sized_signal:
                    continue
                
                # Apply stop loss
                signal_with_sl = self._apply_stop_loss(sized_signal)
                
                # Apply take profit
                signal_with_tp = self._apply_take_profit(signal_with_sl)
                
                # Check portfolio risk limits
                if self._check_portfolio_risk_limits(signal_with_tp):
                    filtered_signals.append(signal_with_tp)
                    
            except Exception as e:
                self.logger.error(f"Error applying risk management to signal: {str(e)}")
        
        # Log filtered signals summary
        original_count = len(signals)
        filtered_count = len(filtered_signals)
        if original_count > 0:
            self.logger.info(f"Applied risk management: {filtered_count}/{original_count} signals passed")
        
        return filtered_signals
    
    def _update_account_info(self) -> None:
        """Update account information and current exposure."""
        # Get account balance
        balance = self.exchange.fetch_balance()
        
        # Get open positions
        open_orders = self.exchange.fetch_open_orders()
        
        # Calculate total portfolio value in base currency
        total_value = 0.0
        
        # Add up all assets in the account
        if 'total' in balance:
            for asset, amount in balance['total'].items():
                if amount > 0:
                    # Convert to base currency if not already
                    if asset != 'USDT':  # Assuming USDT is the base currency
                        try:
                            pair = f"{asset}/USDT"
                            price = self.data_provider.get_latest_price(pair)
                            asset_value = amount * price
                        except Exception:
                            # If pair not found, skip this asset
                            continue
                    else:
                        asset_value = amount
                    
                    total_value += asset_value
        
        # Update state
        self.total_portfolio_value = total_value
        self.open_positions = {}
        self.total_exposure = 0.0
        self.pair_exposure = {}
        
        # Calculate exposure from open positions
        for order in open_orders:
            pair = order['symbol']
            side = order['side']
            amount = order['amount']
            remaining = order.get('remaining', amount)
            
            if side == 'buy':
                # For buy orders, exposure is the amount to spend
                exposure = remaining * order['price']
            else:
                # For sell orders, exposure is the crypto amount
                exposure = remaining
            
            # Track open positions
            if pair not in self.open_positions:
                self.open_positions[pair] = []
            
            self.open_positions[pair].append(order)
            
            # Update exposure
            if pair not in self.pair_exposure:
                self.pair_exposure[pair] = 0.0
            
            self.pair_exposure[pair] += exposure
            self.total_exposure += exposure
        
        self.logger.debug(f"Portfolio value: {total_value:.2f}, Total exposure: {self.total_exposure:.2f}")
    
    def _apply_position_sizing(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply position sizing to a signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            Signal with adjusted position size, or None if rejected
        """
        # Make a copy of the signal to avoid modifying the original
        adjusted_signal = signal.copy()
        
        pair = signal['pair']
        action = signal['action']
        
        # Get current price
        current_price = self.data_provider.get_latest_price(pair)
        if current_price <= 0:
            self.logger.warning(f"Invalid price for {pair}, skipping position sizing")
            return None
        
        # Calculate position size
        position_sizing = self._calculate_position_size(
            pair=pair,
            action=action,
            price=current_price,
            signal=signal
        )
        
        if position_sizing is None:
            self.logger.warning(f"Position sizing failed for {pair}, rejecting signal")
            return None
        
        # Update signal with calculated position size
        adjusted_signal['amount'] = position_sizing.amount
        adjusted_signal['position_value'] = position_sizing.position_value
        adjusted_signal['risk_amount'] = position_sizing.risk_amount
        adjusted_signal['risk_percent'] = position_sizing.risk_percent
        
        self.logger.debug(
            f"Position sizing for {pair} ({action}): "
            f"Amount={position_sizing.amount:.6f}, "
            f"Value={position_sizing.position_value:.2f}, "
            f"Risk={position_sizing.risk_amount:.2f} ({position_sizing.risk_percent*100:.2f}%)"
        )
        
        return adjusted_signal
    
    def _calculate_position_size(self, pair: str, action: str, price: float,
                               signal: Dict[str, Any]) -> Optional[PositionSizing]:
        """
        Calculate position size based on risk parameters.
        
        Args:
            pair: Trading pair
            action: 'buy' or 'sell'
            price: Current price
            signal: Trading signal
            
        Returns:
            PositionSizing object or None if calculation fails
        """
        # Get sizing method from config
        method = self.position_sizing_config.get('method', 'risk_based')
        
        # Calculate position size based on method
        if method == 'fixed':
            # Fixed position size in base currency
            stake_amount = 100  # Hard-coded for simplicity
            amount = stake_amount / price
            risk_amount = stake_amount * self.max_risk_per_trade
            
            return PositionSizing(
                amount=amount,
                risk_amount=risk_amount,
                position_value=stake_amount,
                risk_percent=self.max_risk_per_trade,
                method=method
            )
            
        elif method == 'risk_based':
            # Calculate position size based on risk
            # Get stop loss level
            if 'stop_loss' in signal:
                stop_loss = signal['stop_loss']
            else:
                # If no stop loss in signal, calculate a default one
                volatility = self.data_provider.get_volatility(pair)
                stop_loss_pct = max(0.02, volatility / 100)  # At least 2%
                
                if action == 'buy':
                    stop_loss = price * (1 - stop_loss_pct)
                else:
                    stop_loss = price * (1 + stop_loss_pct)
            
            # Calculate risk per unit
            if action == 'buy':
                risk_per_unit = price - stop_loss
            else:
                risk_per_unit = stop_loss - price
            
            # Check for valid risk_per_unit
            if risk_per_unit <= 0:
                self.logger.warning(f"Invalid risk per unit for {pair}: {risk_per_unit}")
                return None
            
            # Calculate risk amount
            risk_amount = self.total_portfolio_value * self.max_risk_per_trade
            
            # Calculate position size
            amount = risk_amount / risk_per_unit
            position_value = amount * price
            
            # Apply maximum position size limit
            max_position_value = self.total_portfolio_value * 0.2  # Max 20% of portfolio
            if position_value > max_position_value:
                position_value = max_position_value
                amount = position_value / price
                risk_amount = amount * risk_per_unit
            
            return PositionSizing(
                amount=amount,
                risk_amount=risk_amount,
                position_value=position_value,
                risk_percent=risk_amount / self.total_portfolio_value,
                method=method
            )
            
        elif method == 'kelly':
            # Simplified Kelly criterion calculation
            # Would require win rate and average win/loss statistics
            # from backtesting or trading history
            
            # Fallback to risk-based for now
            return self._calculate_position_size(pair, action, price, signal)
        
        else:
            self.logger.warning(f"Unknown position sizing method: {method}")
            return None
    
    def _apply_stop_loss(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply stop loss to a signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            Signal with stop loss applied
        """
        # Check if stop loss is already in the signal
        if 'stop_loss' in signal:
            return signal
        
        # Check if stop loss is enabled
        if not self.stop_loss_config.get('enabled', True):
            return signal
        
        # Make a copy of the signal
        adjusted_signal = signal.copy()
        
        # Get stop loss parameters
        stop_loss_type = self.stop_loss_config.get('type', 'fixed')
        stop_loss_percentage = self.stop_loss_config.get('percentage', 0.05)
        atr_multiplier = self.stop_loss_config.get('atr_multiplier', 2)
        
        pair = signal['pair']
        action = signal['action']
        price = self.data_provider.get_latest_price(pair)
        
        if stop_loss_type == 'fixed':
            # Fixed percentage stop loss
            if action == 'buy':
                stop_loss = price * (1 - stop_loss_percentage)
            else:
                stop_loss = price * (1 + stop_loss_percentage)
                
        elif stop_loss_type == 'atr':
            # ATR-based stop loss
            df = self.data_provider.get_ohlcv(pair)
            
            if df.empty:
                # Fallback to fixed if no data
                if action == 'buy':
                    stop_loss = price * (1 - stop_loss_percentage)
                else:
                    stop_loss = price * (1 + stop_loss_percentage)
            else:
                atr = df['atr'].iloc[-1]
                
                if action == 'buy':
                    stop_loss = price - (atr * atr_multiplier)
                else:
                    stop_loss = price + (atr * atr_multiplier)
                    
        elif stop_loss_type == 'trailing':
            # For trailing stop, we set initial stop loss same as fixed
            # The actual trailing functionality will be implemented in order management
            if action == 'buy':
                stop_loss = price * (1 - stop_loss_percentage)
            else:
                stop_loss = price * (1 + stop_loss_percentage)
            
            # Mark as trailing for order execution
            adjusted_signal['trailing_stop'] = True
            
        else:
            # Default to fixed percentage
            if action == 'buy':
                stop_loss = price * (1 - stop_loss_percentage)
            else:
                stop_loss = price * (1 + stop_loss_percentage)
        
        # Round stop loss to 8 decimal places
        stop_loss = round(stop_loss, 8)
        
        # Add stop loss to signal
        adjusted_signal['stop_loss'] = stop_loss
        
        return adjusted_signal
    
    def _apply_take_profit(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply take profit to a signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            Signal with take profit applied
        """
        # Check if take profit is already in the signal
        if 'take_profit' in signal:
            return signal
        
        # Check if take profit is enabled
        if not self.take_profit_config.get('enabled', True):
            return signal
        
        # Make a copy of the signal
        adjusted_signal = signal.copy()
        
        # Get take profit parameters
        take_profit_type = self.take_profit_config.get('type', 'fixed')
        take_profit_percentage = self.take_profit_config.get('percentage', 0.1)
        
        pair = signal['pair']
        action = signal['action']
        price = self.data_provider.get_latest_price(pair)
        
        if take_profit_type == 'fixed':
            # Fixed percentage take profit
            if action == 'buy':
                take_profit = price * (1 + take_profit_percentage)
            else:
                take_profit = price * (1 - take_profit_percentage)
                
        elif take_profit_type == 'scaled':
            # Scaled take profit levels
            scaled_levels = self.take_profit_config.get('scaled_levels', [0.05, 0.1, 0.2])
            
            # Calculate take profit levels
            if action == 'buy':
                take_profit = [price * (1 + level) for level in scaled_levels]
            else:
                take_profit = [price * (1 - level) for level in scaled_levels]
                
        elif take_profit_type == 'adaptive':
            # Adaptive take profit based on market conditions
            df = self.data_provider.get_ohlcv(pair)
            
            if df.empty:
                # Fallback to fixed if no data
                if action == 'buy':
                    take_profit = price * (1 + take_profit_percentage)
                else:
                    take_profit = price * (1 - take_profit_percentage)
            else:
                # Calculate volatility
                returns = df['close'].pct_change().dropna()
                volatility = returns.tail(20).std() * 100  # Annualized volatility
                
                # Adjust take profit based on volatility
                adjusted_tp_percentage = max(0.05, volatility / 10)  # Minimum 5%
                
                if action == 'buy':
                    take_profit = price * (1 + adjusted_tp_percentage)
                else:
                    take_profit = price * (1 - adjusted_tp_percentage)
        else:
            # Default to fixed percentage
            if action == 'buy':
                take_profit = price * (1 + take_profit_percentage)
            else:
                take_profit = price * (1 - take_profit_percentage)
        
        # Round take profit to 8 decimal places (or each level if it's a list)
        if isinstance(take_profit, list):
            take_profit = [round(tp, 8) for tp in take_profit]
        else:
            take_profit = round(take_profit, 8)
        
        # Add take profit to signal
        adjusted_signal['take_profit'] = take_profit
        
        return adjusted_signal
    
    def _check_portfolio_risk_limits(self, signal: Dict[str, Any]) -> bool:
        """
        Check if signal complies with portfolio risk limits.
        
        Args:
            signal: Trading signal
            
        Returns:
            True if signal passes risk checks, False otherwise
        """
        pair = signal['pair']
        position_value = signal.get('position_value', 0)
        
        # Check maximum open trades limit
        max_open_trades = 5  # Hardcoded for simplicity
        if len(self.open_positions) >= max_open_trades and pair not in self.open_positions:
            self.logger.info(f"Rejecting signal: Maximum open trades limit reached ({max_open_trades})")
            return False
        
        # Check maximum portfolio exposure
        max_exposure_pct = 0.5  # Maximum 50% of portfolio exposed
        current_exposure_pct = self.total_exposure / self.total_portfolio_value
        signal_exposure_pct = position_value / self.total_portfolio_value
        
        if current_exposure_pct + signal_exposure_pct > max_exposure_pct:
            self.logger.info(
                f"Rejecting signal: Maximum portfolio exposure would be exceeded "
                f"({(current_exposure_pct + signal_exposure_pct)*100:.1f}% > {max_exposure_pct*100:.1f}%)"
            )
            return False
        
        # Check maximum exposure per pair
        max_pair_exposure_pct = 0.2  # Maximum 20% per pair
        current_pair_exposure = self.pair_exposure.get(pair, 0)
        current_pair_exposure_pct = current_pair_exposure / self.total_portfolio_value
        
        if current_pair_exposure_pct + signal_exposure_pct > max_pair_exposure_pct:
            self.logger.info(
                f"Rejecting signal: Maximum exposure for {pair} would be exceeded "
                f"({(current_pair_exposure_pct + signal_exposure_pct)*100:.1f}% > {max_pair_exposure_pct*100:.1f}%)"
            )
            return False
        
        # Additional checks can be added here
        
        return True 