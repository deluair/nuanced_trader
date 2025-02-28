#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Backtesting Module for Nuanced Trader
--------------------------------------

This module provides backtesting functionality for testing trading strategies
against historical data before deploying them in a live environment.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from loguru import logger
from typing import Dict, List, Any, Tuple, Optional

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_loader import ConfigLoader
from data.data_provider import DataProvider
from strategies.strategy_factory import StrategyFactory
from risk_management.risk_manager import RiskManager
from utils.performance_metrics import calculate_sharpe_ratio, calculate_max_drawdown, calculate_win_rate, generate_performance_summary

@dataclass
class TradeResult:
    """Data class to store individual trade results"""
    pair: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    action: str  # 'buy' or 'sell'
    amount: float
    profit_loss: float = 0
    profit_loss_pct: float = 0
    status: str = "open"  # 'open', 'closed', 'stopped_out', 'take_profit'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trade_id: str = ""
    
    def close_trade(self, exit_time: datetime, exit_price: float, status: str = "closed"):
        """Close a trade and calculate profit/loss"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.status = status
        
        # Calculate profit/loss
        if self.action == "buy":
            self.profit_loss = (exit_price - self.entry_price) * self.amount
            self.profit_loss_pct = (exit_price / self.entry_price - 1) * 100
        else:  # sell/short
            self.profit_loss = (self.entry_price - exit_price) * self.amount
            self.profit_loss_pct = (self.entry_price / exit_price - 1) * 100
        
        return self.profit_loss


class BacktestResult:
    """Class to store and analyze backtest results"""
    
    def __init__(self, strategy_name: str, params: Dict[str, Any], start_date: datetime, end_date: datetime):
        self.strategy_name = strategy_name
        self.strategy_params = params
        self.start_date = start_date
        self.end_date = end_date
        self.trades: List[TradeResult] = []
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit_loss = 0
        self.win_rate = 0
        self.profit_factor = 0
        self.max_drawdown = 0
        self.max_drawdown_pct = 0
        self.sharpe_ratio = 0
        self.equity_curve = []
        self.daily_returns = []
        
    def add_trade(self, trade: TradeResult):
        """Add a trade to the results"""
        self.trades.append(trade)
        
    def calculate_metrics(self, initial_capital: float = 10000):
        """Calculate performance metrics"""
        if not self.trades:
            return
            
        self.total_trades = len(self.trades)
        
        # Calculate profit/loss metrics
        self.winning_trades = len([t for t in self.trades if t.profit_loss > 0])
        self.losing_trades = len([t for t in self.trades if t.profit_loss < 0])
        
        self.total_profit_loss = sum(trade.profit_loss for trade in self.trades)
        
        # Win rate and profit factor
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        total_gains = sum(max(0, trade.profit_loss) for trade in self.trades)
        total_losses = sum(abs(min(0, trade.profit_loss)) for trade in self.trades)
        self.profit_factor = total_gains / total_losses if total_losses > 0 else float('inf')
        
        # Build equity curve
        equity = initial_capital
        equity_curve = [equity]
        
        # Sort trades by entry time
        sorted_trades = sorted(self.trades, key=lambda x: x.entry_time)
        
        for trade in sorted_trades:
            equity += trade.profit_loss
            equity_curve.append(equity)
            
        self.equity_curve = equity_curve
        
        # Calculate drawdown
        running_max = 0
        drawdown = []
        
        for equity_point in equity_curve:
            running_max = max(running_max, equity_point)
            drawdown.append(running_max - equity_point)
            
        self.max_drawdown = max(drawdown) if drawdown else 0
        self.max_drawdown_pct = (self.max_drawdown / running_max) * 100 if running_max > 0 else 0
        
        # Calculate daily returns
        # Group trades by day and calculate cumulative P&L
        if len(sorted_trades) > 0:
            min_date = min(t.entry_time.date() for t in sorted_trades)
            max_date = max(t.exit_time.date() if t.exit_time else t.entry_time.date() for t in sorted_trades)
            date_range = pd.date_range(min_date, max_date)
            
            daily_pnl = {}
            for day in date_range:
                day_key = day.strftime('%Y-%m-%d')
                daily_pnl[day_key] = 0
            
            for trade in sorted_trades:
                if trade.exit_time:
                    exit_day = trade.exit_time.strftime('%Y-%m-%d')
                    if exit_day in daily_pnl:
                        daily_pnl[exit_day] += trade.profit_loss
            
            self.daily_returns = list(daily_pnl.values())
            
            # Calculate Sharpe ratio
            if len(self.daily_returns) > 1:
                self.sharpe_ratio = calculate_sharpe_ratio(self.daily_returns)
        
    def generate_report(self, output_dir: str = "backtest_results") -> str:
        """Generate a performance report and save it to a file"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.strategy_name}_{timestamp}"
        report_path = os.path.join(output_dir, f"{filename}.json")
        
        report = {
            "strategy_name": self.strategy_name,
            "strategy_params": self.strategy_params,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_profit_loss": self.total_profit_loss,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "trades": [
                {
                    "pair": t.pair,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "action": t.action,
                    "amount": t.amount,
                    "profit_loss": t.profit_loss,
                    "profit_loss_pct": t.profit_loss_pct,
                    "status": t.status
                }
                for t in self.trades
            ]
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
        
        # Generate performance charts
        self._generate_performance_charts(output_dir, filename)
        
        return report_path
        
    def _generate_performance_charts(self, output_dir: str, filename: str):
        """Generate performance charts"""
        if not self.trades:
            return
            
        # Set style
        sns.set_style("whitegrid")
        
        # Create figure with multiple subplots
        fig, axes = plt.subplots(3, 1, figsize=(12, 18))
        
        # Plot equity curve
        axes[0].plot(self.equity_curve)
        axes[0].set_title('Equity Curve')
        axes[0].set_xlabel('Trade Number')
        axes[0].set_ylabel('Account Balance')
        
        # Plot drawdowns
        running_max = np.maximum.accumulate(self.equity_curve)
        drawdown = (running_max - self.equity_curve) / running_max * 100
        axes[1].fill_between(range(len(drawdown)), 0, drawdown, color='red', alpha=0.3)
        axes[1].set_title('Drawdown (%)')
        axes[1].set_xlabel('Trade Number')
        axes[1].set_ylabel('Drawdown %')
        
        # Plot trade P&L
        profit_loss = [t.profit_loss for t in self.trades]
        colors = ['green' if pl >= 0 else 'red' for pl in profit_loss]
        axes[2].bar(range(len(profit_loss)), profit_loss, color=colors)
        axes[2].set_title('Trade P&L')
        axes[2].set_xlabel('Trade Number')
        axes[2].set_ylabel('Profit/Loss')
        
        plt.tight_layout()
        chart_path = os.path.join(output_dir, f"{filename}_charts.png")
        plt.savefig(chart_path)
        plt.close()


class Backtester:
    """
    Backtester class for testing trading strategies against historical data.
    """
    
    def __init__(self, config_path: str = None, start_date: str = None, end_date: str = None):
        """
        Initialize the backtester.
        
        Args:
            config_path: Path to the configuration file
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
        """
        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.get_config()
        
        # Set backtest dates
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        
        # Initialize components
        self._initialize_components()
        
        # Backtest results
        self.results = {
            "trades": [],
            "equity_curve": [],
            "dates": []
        }
        
        logger.info("Backtester initialized")
    
    def _initialize_components(self):
        """Initialize all backtester components."""
        # Setup data provider (mock exchange client for backtesting)
        self.data_provider = DataProvider(
            exchange=None,  # We'll load historical data directly
            timeframe=self.config["exchange"]["timeframe"],
            trading_pairs=self.config["exchange"]["trading_pairs"],
            data_directory=self.config["general"]["data_directory"],
            cache_data=True
        )
        
        # Initialize strategy
        strategy_name = self.config["strategy"]["name"]
        strategy_params = self.config["strategy"]["parameters"]
        self.strategy = StrategyFactory.create_strategy(
            strategy_name=strategy_name,
            parameters=strategy_params,
            data_provider=self.data_provider
        )
        
        # Initialize account state
        self.account = {
            "balance": 10000.0,  # Starting with $10,000
            "positions": {},     # Current open positions
            "equity_history": [10000.0]  # Track equity over time
        }
    
    def run(self):
        """Run the backtest."""
        logger.info(f"Starting backtest from {self.start_date} to {self.end_date}")
        
        # Load historical data
        self._load_historical_data()
        
        # Iterate through each date in the backtest period
        current_date = self.start_date
        date_index = 0
        
        while current_date <= self.end_date:
            # Skip weekends in traditional markets (optional for crypto)
            # if current_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            #     current_date += timedelta(days=1)
            #     continue
            
            logger.info(f"Processing date: {current_date.strftime('%Y-%m-%d')}")
            
            # Update data for current date
            self._update_data_to_date(current_date)
            
            # Generate signals
            signals = self.strategy.generate_signals()
            
            # Execute trades based on signals
            self._execute_trades(signals, current_date)
            
            # Update equity curve
            self._update_equity(current_date)
            
            # Move to next date
            current_date += timedelta(days=1)
            date_index += 1
        
        # Generate performance report
        self._generate_performance_report()
        
        return self.results
    
    def _load_historical_data(self):
        """Load historical data for all trading pairs."""
        # This is a placeholder - in a real implementation, you would:
        # 1. Load data from CSV files, databases, or APIs
        # 2. Preprocess the data for use in the backtest
        pass
    
    def _update_data_to_date(self, date: datetime):
        """
        Update the data provider to reflect data available up to a specific date.
        
        Args:
            date: The date to update data to
        """
        # In a real implementation, you would filter the historical data
        # to only include data up to the current backtest date
        pass
    
    def _execute_trades(self, signals: List[Dict[str, Any]], date: datetime):
        """
        Execute trades based on signals.
        
        Args:
            signals: List of trading signals
            date: Current backtest date
        """
        for signal in signals:
            pair = signal["pair"]
            action = signal["action"]
            amount = signal["amount"]
            
            # Get the current price from historical data
            price = self._get_price_at_date(pair, date)
            
            if price is None:
                logger.warning(f"No price data for {pair} on {date}, skipping signal")
                continue
            
            # Execute the trade
            if action == "buy":
                self._execute_buy(pair, amount, price, date)
            elif action == "sell":
                self._execute_sell(pair, amount, price, date)
    
    def _get_price_at_date(self, pair: str, date: datetime) -> Optional[float]:
        """
        Get the price of a pair at a specific date.
        
        Args:
            pair: Trading pair
            date: Date to get price for
            
        Returns:
            Price or None if not available
        """
        # In a real implementation, you would retrieve the price from your historical data
        # This is a placeholder
        return 50000.0 if "BTC" in pair else 3000.0  # Dummy prices
    
    def _execute_buy(self, pair: str, amount: float, price: float, date: datetime):
        """
        Execute a buy order in the backtest.
        
        Args:
            pair: Trading pair
            amount: Amount to buy (in quote currency)
            price: Current price
            date: Trade date
        """
        # Calculate the amount of base currency to buy
        base_amount = amount / price
        
        # Check if we have enough balance
        if amount > self.account["balance"]:
            logger.warning(f"Insufficient balance for buy order: {amount} > {self.account['balance']}")
            return
        
        # Update account balance
        self.account["balance"] -= amount
        
        # Update positions
        if pair not in self.account["positions"]:
            self.account["positions"][pair] = 0
        
        self.account["positions"][pair] += base_amount
        
        # Record the trade
        trade = {
            "pair": pair,
            "action": "buy",
            "amount": base_amount,
            "price": price,
            "value": amount,
            "date": date.strftime("%Y-%m-%d"),
            "fees": amount * 0.001  # Assume 0.1% trading fee
        }
        
        self.results["trades"].append(trade)
        logger.info(f"Executed buy: {base_amount} {pair} at {price}")
    
    def _execute_sell(self, pair: str, amount: float, price: float, date: datetime):
        """
        Execute a sell order in the backtest.
        
        Args:
            pair: Trading pair
            amount: Amount to sell (in base currency)
            price: Current price
            date: Trade date
        """
        # Check if we have the position
        if pair not in self.account["positions"] or self.account["positions"][pair] < amount:
            logger.warning(f"Insufficient position for sell order: {pair} {amount}")
            return
        
        # Calculate the value in quote currency
        quote_amount = amount * price
        
        # Update account balance
        self.account["balance"] += quote_amount
        
        # Update positions
        self.account["positions"][pair] -= amount
        
        # Record the trade
        trade = {
            "pair": pair,
            "action": "sell",
            "amount": amount,
            "price": price,
            "value": quote_amount,
            "date": date.strftime("%Y-%m-%d"),
            "fees": quote_amount * 0.001  # Assume 0.1% trading fee
        }
        
        self.results["trades"].append(trade)
        logger.info(f"Executed sell: {amount} {pair} at {price}")
    
    def _update_equity(self, date: datetime):
        """
        Update the equity curve with the current account value.
        
        Args:
            date: Current backtest date
        """
        # Calculate current positions value
        positions_value = 0
        for pair, amount in self.account["positions"].items():
            price = self._get_price_at_date(pair, date)
            if price is not None:
                positions_value += amount * price
        
        # Total equity = cash balance + positions value
        total_equity = self.account["balance"] + positions_value
        
        # Update equity history
        self.account["equity_history"].append(total_equity)
        
        # Update results
        self.results["equity_curve"].append(total_equity)
        self.results["dates"].append(date)
    
    def _generate_performance_report(self):
        """Generate a performance report from the backtest results."""
        if not self.results["trades"] or not self.results["equity_curve"]:
            logger.warning("No trades or equity data to generate performance report")
            return
        
        # Calculate performance metrics
        performance = generate_performance_summary(
            self.results["trades"],
            self.results["equity_curve"],
            [d.strftime("%Y-%m-%d") for d in self.results["dates"]]
        )
        
        # Print performance summary
        logger.info("=== Backtest Performance Summary ===")
        logger.info(f"Total Return: {performance['total_return_pct']:.2f}%")
        logger.info(f"CAGR: {performance['cagr_pct']:.2f}%")
        logger.info(f"Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        logger.info(f"Max Drawdown: {performance['max_drawdown_pct']:.2f}%")
        logger.info(f"Win Rate: {performance['win_rate']*100:.2f}%")
        logger.info(f"Total Trades: {performance['total_trades']}")
        
        # Add performance to results
        self.results["performance"] = performance
        
        # Plot equity curve
        self._plot_equity_curve()
    
    def _plot_equity_curve(self):
        """Plot the equity curve from the backtest."""
        plt.figure(figsize=(12, 6))
        plt.plot(self.results["dates"], self.results["equity_curve"])
        plt.title("Backtest Equity Curve")
        plt.xlabel("Date")
        plt.ylabel("Equity ($)")
        plt.grid(True)
        
        # Save the plot
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, "equity_curve.png"))
        
        logger.info(f"Equity curve saved to {output_dir}/equity_curve.png")


def main():
    """Main function to run a backtest from the command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nuanced Trader Backtester")
    parser.add_argument("-c", "--config", help="Path to configuration file")
    parser.add_argument("-s", "--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("-e", "--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("-p", "--plot", action="store_true", help="Show plots")
    
    args = parser.parse_args()
    
    # Run backtest
    backtester = Backtester(
        config_path=args.config,
        start_date=args.start or "2023-01-01",
        end_date=args.end
    )
    
    results = backtester.run()
    
    # Save results to JSON
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "backtest_results.json"), "w") as f:
        # Convert datetime objects to strings
        results_json = {
            "trades": results["trades"],
            "equity_curve": results["equity_curve"],
            "dates": [d.strftime("%Y-%m-%d") if isinstance(d, datetime) else d for d in results["dates"]],
            "performance": results["performance"]
        }
        json.dump(results_json, f, indent=2)
    
    logger.info(f"Backtest results saved to {output_dir}/backtest_results.json")
    
    # Show plots if requested
    if args.plot:
        plt.show()


if __name__ == "__main__":
    main()
