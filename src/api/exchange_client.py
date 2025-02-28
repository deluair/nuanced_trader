#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exchange Client
--------------

This module provides an interface to cryptocurrency exchanges using the CCXT library.
"""

import ccxt
import time
import pandas as pd
import numpy as np
import logging
import os
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
import json
import hmac
import hashlib
import requests
from ratelimit import limits, sleep_and_retry
from loguru import logger


class ExchangeClient:
    """
    Exchange client for interacting with cryptocurrency exchanges.
    """
    
    def __init__(self, exchange_name: str, paper_trading: bool = True,
                 api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 additional_params: Optional[Dict[str, Any]] = None):
        """
        Initialize the exchange client.
        
        Args:
            exchange_name: Name of the exchange (e.g., 'binance', 'coinbase', 'kraken')
            paper_trading: Whether to use paper trading (if available)
            api_key: API key for the exchange
            api_secret: API secret for the exchange
            additional_params: Additional parameters for exchange initialization
        
        Raises:
            ValueError: If exchange is not supported
        """
        self.exchange_name = exchange_name.lower()
        self.paper_trading = paper_trading
        
        # Check if exchange is supported by CCXT
        if not hasattr(ccxt, self.exchange_name):
            raise ValueError(f"Exchange '{exchange_name}' is not supported by CCXT")
        
        # Initialize exchange parameters
        exchange_params = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # Respect rate limits
        }
        
        # Add sandbox/testnet for paper trading if available
        if paper_trading:
            exchange_params['options'] = {'test': True}
        
        # Add additional parameters if provided
        if additional_params:
            exchange_params.update(additional_params)
        
        # Create exchange instance
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange = exchange_class(exchange_params)
        
        # Initialize markets (load exchange information)
        try:
            logger.info(f"Initializing {exchange_name} exchange...")
            self.exchange.load_markets()
            logger.info(f"Connected to {exchange_name} exchange successfully")
            
            # Log some basic exchange info
            logger.info(f"Exchange has {len(self.exchange.markets)} markets available")
            if paper_trading:
                logger.info("Using paper trading mode")
            
        except ccxt.NetworkError as e:
            logger.error(f"Network error connecting to {exchange_name}: {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error initializing {exchange_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error initializing {exchange_name} exchange: {str(e)}")
            raise
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information.
        
        Returns:
            Dict containing exchange information
        """
        return {
            'name': self.exchange.name,
            'id': self.exchange.id,
            'rateLimit': self.exchange.rateLimit,
            'has': self.exchange.has,
            'urls': self.exchange.urls,
            'version': self.exchange.version,
            'timeframes': self.exchange.timeframes if hasattr(self.exchange, 'timeframes') else {},
            'paper_trading': self.paper_trading,
        }
    
    def get_markets(self) -> Dict[str, Any]:
        """
        Get all available markets.
        
        Returns:
            Dict containing market information
        """
        return self.exchange.markets
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dict containing ticker information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
        """
        try:
            return self.exchange.fetch_ticker(symbol)
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching ticker for {symbol}: {str(e)}")
            raise
    
    def get_orderbook(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            limit: Maximum number of orders to retrieve
            
        Returns:
            Dict containing order book information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
        """
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching order book for {symbol}: {str(e)}")
            raise
    
    def get_ohlcv(self, symbol: str, timeframe: str = '1h', 
                 since: Optional[int] = None, limit: Optional[int] = None) -> List[List[float]]:
        """
        Get OHLCV (candle) data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            since: Timestamp in milliseconds to fetch data from
            limit: Maximum number of candles to fetch
            
        Returns:
            List of lists containing [timestamp, open, high, low, close, volume]
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
        """
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching OHLCV for {symbol} ({timeframe}): {str(e)}")
            raise
    
    def fetch_balance(self) -> Dict[str, Any]:
        """
        Get account balance.
        
        Returns:
            Dict containing balance information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
        """
        try:
            return self.exchange.fetch_balance()
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error fetching balance: {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching balance: {str(e)}")
            raise
    
    def create_market_buy_order(self, symbol: str, amount: float) -> Dict[str, Any]:
        """
        Create a market buy order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            amount: Amount to buy (in base currency)
            
        Returns:
            Dict containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.InsufficientFunds: If insufficient funds
        """
        try:
            return self.exchange.create_market_buy_order(symbol, amount)
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for market buy order ({symbol}, {amount}): {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating market buy order ({symbol}, {amount}): {str(e)}")
            raise
    
    def create_market_sell_order(self, symbol: str, amount: float) -> Dict[str, Any]:
        """
        Create a market sell order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            amount: Amount to sell (in base currency)
            
        Returns:
            Dict containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.InsufficientFunds: If insufficient funds
        """
        try:
            return self.exchange.create_market_sell_order(symbol, amount)
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for market sell order ({symbol}, {amount}): {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating market sell order ({symbol}, {amount}): {str(e)}")
            raise
    
    def create_limit_buy_order(self, symbol: str, amount: float, price: float) -> Dict[str, Any]:
        """
        Create a limit buy order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            amount: Amount to buy (in base currency)
            price: Limit price
            
        Returns:
            Dict containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.InsufficientFunds: If insufficient funds
        """
        try:
            return self.exchange.create_limit_buy_order(symbol, amount, price)
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for limit buy order ({symbol}, {amount} @ {price}): {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating limit buy order ({symbol}, {amount} @ {price}): {str(e)}")
            raise
    
    def create_limit_sell_order(self, symbol: str, amount: float, price: float) -> Dict[str, Any]:
        """
        Create a limit sell order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            amount: Amount to sell (in base currency)
            price: Limit price
            
        Returns:
            Dict containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.InsufficientFunds: If insufficient funds
        """
        try:
            return self.exchange.create_limit_sell_order(symbol, amount, price)
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for limit sell order ({symbol}, {amount} @ {price}): {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating limit sell order ({symbol}, {amount} @ {price}): {str(e)}")
            raise
    
    def create_stop_loss_order(self, symbol: str, amount: float, price: float) -> Dict[str, Any]:
        """
        Create a stop loss order.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            amount: Amount (in base currency)
            price: Stop price
            
        Returns:
            Dict containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.NotSupported: If stop loss orders are not supported
        """
        try:
            # Check if exchange supports stop loss orders
            if not self.exchange.has['createStopLossOrder']:
                # Try to create stop market order as fallback
                if self.exchange.has['createStopMarketOrder']:
                    return self.exchange.create_stop_market_order(symbol, 'sell', amount, price)
                
                # Try to use create_order with stop-loss params as fallback
                params = {'stopPrice': price, 'type': 'stop_loss', 'side': 'sell'}
                return self.exchange.create_order(symbol, 'market', 'sell', amount, None, params)
            
            # Use native stop loss method if available
            return self.exchange.create_stop_loss_order(symbol, 'sell', amount, price)
        
        except ccxt.NotSupported:
            logger.error(f"Stop loss orders not supported by {self.exchange_name}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating stop loss order ({symbol}, {amount} @ {price}): {str(e)}")
            raise
    
    def fetch_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch an order by ID.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol (required by some exchanges)
            
        Returns:
            Dict containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.OrderNotFound: If order not found
        """
        try:
            return self.exchange.fetch_order(order_id, symbol)
        except ccxt.OrderNotFound as e:
            logger.error(f"Order not found ({order_id}): {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching order ({order_id}): {str(e)}")
            raise
    
    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch all open orders.
        
        Args:
            symbol: Trading pair symbol (optional)
            
        Returns:
            List of dicts containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
        """
        try:
            return self.exchange.fetch_open_orders(symbol)
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching open orders: {str(e)}")
            raise
    
    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an order by ID.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol (required by some exchanges)
            
        Returns:
            Dict containing order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.OrderNotFound: If order not found
        """
        try:
            return self.exchange.cancel_order(order_id, symbol)
        except ccxt.OrderNotFound as e:
            logger.error(f"Order not found to cancel ({order_id}): {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error cancelling order ({order_id}): {str(e)}")
            raise
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Cancel all open orders.
        
        Args:
            symbol: Trading pair symbol (optional)
            
        Returns:
            List of dicts containing cancelled order information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
            ccxt.NotSupported: If not supported by exchange
        """
        try:
            if self.exchange.has['cancelAllOrders']:
                return self.exchange.cancel_all_orders(symbol)
            else:
                # Fallback: fetch open orders and cancel them one by one
                open_orders = self.fetch_open_orders(symbol)
                cancelled_orders = []
                
                for order in open_orders:
                    cancelled_order = self.cancel_order(order['id'], order['symbol'])
                    cancelled_orders.append(cancelled_order)
                
                return cancelled_orders
        
        except ccxt.NotSupported:
            logger.error(f"Cancel all orders not supported by {self.exchange_name}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error cancelling all orders: {str(e)}")
            raise
    
    def fetch_trades(self, symbol: str, since: Optional[int] = None, 
                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch trades for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            since: Timestamp in milliseconds to fetch trades from
            limit: Maximum number of trades to fetch
            
        Returns:
            List of dicts containing trade information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
        """
        try:
            return self.exchange.fetch_trades(symbol, since, limit)
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching trades for {symbol}: {str(e)}")
            raise
    
    def fetch_my_trades(self, symbol: Optional[str] = None, since: Optional[int] = None,
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch user's trades.
        
        Args:
            symbol: Trading pair symbol (optional)
            since: Timestamp in milliseconds to fetch trades from
            limit: Maximum number of trades to fetch
            
        Returns:
            List of dicts containing trade information
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
            ccxt.AuthenticationError: If authentication fails
        """
        try:
            return self.exchange.fetch_my_trades(symbol, since, limit)
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error fetching my trades: {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching my trades: {str(e)}")
            raise
    
    def get_server_time(self) -> int:
        """
        Get server timestamp in milliseconds.
        
        Returns:
            Server timestamp in milliseconds
            
        Raises:
            ccxt.ExchangeError: If exchange error occurs
        """
        try:
            return self.exchange.milliseconds()
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error getting server time: {str(e)}")
            raise 


class BinanceClient(ExchangeClient):
    """Client specifically for Binance exchange with additional features"""
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 use_testnet: bool = False):
        """
        Initialize the Binance client
        
        Args:
            api_key: Binance API key
            secret_key: Binance secret key
            use_testnet: Whether to use the Binance testnet
        """
        # Set up additional parameters for Binance
        additional_params = {
            'options': {
                'defaultType': 'spot',  # Use spot trading by default
                'adjustForTimeDifference': True  # Adjust for time difference
            }
        }
        
        # Use testnet URL if specified
        if use_testnet:
            additional_params['urls'] = {
                'api': 'https://testnet.binance.vision/api'
            }
        
        super().__init__('binance', api_key, secret_key, additional_params, use_testnet)
    
    @sleep_and_retry
    @limits(calls=10, period=1)  # Binance-specific rate limit
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', 
                   since: Optional[int] = None, limit: Optional[int] = 1000) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Binance with optimized parameters
        """
        # Call the parent method with Binance-specific tweaks
        df = super().fetch_ohlcv(symbol, timeframe, since, limit)
        
        # Apply any Binance-specific post-processing if needed
        if df is not None:
            # Binance sometimes includes incomplete candles - we might want to drop the last one
            if not pd.Timestamp.utcnow().floor(timeframe) == df.index[-1]:
                df = df.iloc[:-1]
        
        return df
    
    def get_futures_account_info(self):
        """Get futures account information (Binance-specific)"""
        try:
            # Set the type to futures
            self.exchange.options['defaultType'] = 'future'
            
            # Fetch the futures account info
            account_info = self.exchange.fapiPrivateGetAccount()
            
            # Reset back to spot
            self.exchange.options['defaultType'] = 'spot'
            
            return account_info
            
        except Exception as e:
            logger.error(f"Error fetching futures account info: {e}")
            
            # Reset back to spot
            self.exchange.options['defaultType'] = 'spot'
            
            return None
    
    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for a futures symbol (Binance-specific)"""
        try:
            # Set the type to futures
            self.exchange.options['defaultType'] = 'future'
            
            # Format the symbol for futures
            market_symbol = self._format_symbol(symbol)
            
            # Set the leverage
            result = self.exchange.fapiPrivatePostLeverage({
                'symbol': market_symbol.replace('/', ''),
                'leverage': leverage
            })
            
            # Reset back to spot
            self.exchange.options['defaultType'] = 'spot'
            
            return result
            
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            
            # Reset back to spot
            self.exchange.options['defaultType'] = 'spot'
            
            return None


class CoinbaseClient(ExchangeClient):
    """Client specifically for Coinbase Pro exchange with additional features"""
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 passphrase: Optional[str] = None, sandbox_mode: bool = False):
        """
        Initialize the Coinbase Pro client
        
        Args:
            api_key: Coinbase API key
            secret_key: Coinbase secret key
            passphrase: Coinbase API passphrase
            sandbox_mode: Whether to use sandbox mode
        """
        # Coinbase Pro requires a passphrase
        additional_params = {}
        if passphrase:
            additional_params['password'] = passphrase
        
        super().__init__('coinbasepro', api_key, secret_key, additional_params, sandbox_mode)
    
    def _format_symbol(self, symbol: str) -> str:
        """Format the symbol for Coinbase Pro"""
        # Coinbase Pro uses '-' instead of '/' in some API endpoints
        if '/' in symbol:
            return symbol
        else:
            return symbol.replace('-', '/')


# Factory function to create appropriate exchange client
def create_exchange_client(exchange_name: str, api_key: Optional[str] = None, 
                         secret_key: Optional[str] = None, **kwargs) -> ExchangeClient:
    """
    Create an exchange client based on the exchange name
    
    Args:
        exchange_name: Name of the exchange ('binance', 'coinbase', etc.)
        api_key: API key for the exchange
        secret_key: Secret key for the exchange
        **kwargs: Additional parameters for specific exchanges
        
    Returns:
        ExchangeClient instance
    """
    exchange_name = exchange_name.lower()
    
    if exchange_name == 'binance':
        return BinanceClient(api_key, secret_key, kwargs.get('use_testnet', False))
    elif exchange_name == 'coinbase' or exchange_name == 'coinbasepro':
        return CoinbaseClient(api_key, secret_key, kwargs.get('passphrase'), kwargs.get('sandbox_mode', False))
    else:
        # Generic exchange client
        return ExchangeClient(exchange_name, api_key, secret_key, kwargs.get('additional_params'), 
                            kwargs.get('sandbox_mode', False)) 