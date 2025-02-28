#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
NuancedTrader - Main execution file
-----------------------------------

This is the main entry point for running the trading bot.
It initializes all components, handles configuration, and orchestrates
the trading process.
"""

import os
import sys
import time
import signal
import argparse
import yaml
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
import schedule

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import bot components
from src.api.exchange_client import ExchangeClient
from src.utils.config_loader import ConfigLoader
from src.utils.logger_setup import setup_logger
from src.strategies.strategy_factory import StrategyFactory
from src.risk_management.risk_manager import RiskManager
from src.data.data_provider import DataProvider
from src.utils.notification_manager import NotificationManager

class TradingBot:
    """
    Main trading bot class that orchestrates all components.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the trading bot.
        
        Args:
            config_path: Path to the configuration file
        """
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.get_config()
        
        # Setup logger
        setup_logger(self.config["general"]["log_level"])
        logger.info("Initializing trading bot...")
        
        # Initialize components
        self._initialize_components()
        
        # Track running state
        self.is_running = False
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
    
    def _initialize_components(self):
        """Initialize all bot components based on configuration."""
        logger.info("Initializing bot components...")
        
        # Initialize exchange client
        self.exchange = ExchangeClient(
            exchange_name=self.config["exchange"]["name"],
            paper_trading=self.config["exchange"]["paper_trading"],
            api_key=os.getenv(self.config["exchange"]["api_key_env"]),
            api_secret=os.getenv(self.config["exchange"]["api_secret_env"])
        )
        
        # Initialize data provider
        self.data_provider = DataProvider(
            exchange=self.exchange,
            timeframe=self.config["exchange"]["timeframe"],
            trading_pairs=self.config["exchange"]["trading_pairs"],
            data_directory=self.config["general"]["data_directory"]
        )
        
        # Initialize strategy
        strategy_name = self.config["strategy"]["name"]
        strategy_params = self.config["strategy"]["parameters"]
        self.strategy = StrategyFactory.create_strategy(
            strategy_name=strategy_name,
            parameters=strategy_params,
            data_provider=self.data_provider
        )
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            config=self.config["risk_management"],
            exchange=self.exchange,
            data_provider=self.data_provider
        )
        
        # Initialize notification manager
        self.notification_manager = NotificationManager(
            config=self.config["notifications"]
        )
        
        logger.info("Bot components initialized successfully")
    
    def start(self):
        """Start the trading bot."""
        if self.is_running:
            logger.warning("Trading bot is already running")
            return
        
        self.is_running = True
        logger.info("Starting trading bot...")
        
        # Notify start
        self.notification_manager.send_message("Trading bot started")
        
        # Set up schedules based on timeframe
        self._setup_schedules()
        
        # Main loop
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            self.stop()
    
    def _setup_schedules(self):
        """Set up scheduled tasks based on the configured timeframe."""
        timeframe = self.config["exchange"]["timeframe"]
        
        # Convert timeframe to schedule format
        if timeframe == "1m":
            schedule.every(1).minutes.do(self._trading_cycle)
        elif timeframe == "5m":
            schedule.every(5).minutes.do(self._trading_cycle)
        elif timeframe == "15m":
            schedule.every(15).minutes.do(self._trading_cycle)
        elif timeframe == "1h":
            schedule.every(1).hours.do(self._trading_cycle)
        elif timeframe == "4h":
            schedule.every(4).hours.do(self._trading_cycle)
        elif timeframe == "1d":
            schedule.every().day.at("00:00").do(self._trading_cycle)
        else:
            logger.error(f"Unsupported timeframe: {timeframe}")
            sys.exit(1)
        
        # Schedule daily summary
        schedule.every().day.at("00:00").do(self._daily_summary)
        
        # Run immediately once
        self._trading_cycle()
    
    def _trading_cycle(self):
        """Execute one full trading cycle."""
        logger.info("Starting trading cycle")
        
        try:
            # Update market data
            self.data_provider.update_data()
            
            # Get trading signals from strategy
            signals = self.strategy.generate_signals()
            
            # Apply risk management to signals
            filtered_signals = self.risk_manager.apply_risk_management(signals)
            
            # Execute trades
            if not self.config["general"]["dry_run"]:
                for signal in filtered_signals:
                    self._execute_trade(signal)
            else:
                logger.info(f"Dry run mode: would execute {len(filtered_signals)} trades")
                for signal in filtered_signals:
                    logger.info(f"Signal: {signal}")
            
            logger.info("Trading cycle completed")
        except Exception as e:
            logger.error(f"Error during trading cycle: {str(e)}")
            self.notification_manager.send_message(f"Error in trading cycle: {str(e)}")
    
    def _execute_trade(self, signal):
        """
        Execute a trade based on a signal.
        
        Args:
            signal: Trading signal with action details
        """
        pair = signal["pair"]
        action = signal["action"]
        amount = signal["amount"]
        price = signal.get("price", None)  # Optional limit price
        
        try:
            if action == "buy":
                if price:
                    order = self.exchange.create_limit_buy_order(pair, amount, price)
                else:
                    order = self.exchange.create_market_buy_order(pair, amount)
            elif action == "sell":
                if price:
                    order = self.exchange.create_limit_sell_order(pair, amount, price)
                else:
                    order = self.exchange.create_market_sell_order(pair, amount)
            
            logger.info(f"Executed {action} order for {pair}: {order}")
            self.notification_manager.send_message(
                f"Executed {action} order for {pair}\n"
                f"Amount: {amount}\n"
                f"Price: {price if price else 'market'}"
            )
            
            # Apply stop loss and take profit if enabled
            self._apply_risk_orders(signal, order)
            
        except Exception as e:
            logger.error(f"Error executing {action} order for {pair}: {str(e)}")
            self.notification_manager.send_message(
                f"Error executing {action} order for {pair}: {str(e)}"
            )
    
    def _apply_risk_orders(self, signal, order):
        """Apply stop loss and take profit orders based on config."""
        if not signal.get("stop_loss") and not signal.get("take_profit"):
            return
        
        pair = signal["pair"]
        
        # Apply stop loss
        if signal.get("stop_loss") and self.config["risk_management"]["stop_loss"]["enabled"]:
            try:
                stop_price = signal["stop_loss"]
                self.exchange.create_stop_loss_order(pair, order["amount"], stop_price)
                logger.info(f"Created stop loss for {pair} at {stop_price}")
            except Exception as e:
                logger.error(f"Error creating stop loss for {pair}: {str(e)}")
        
        # Apply take profit
        if signal.get("take_profit") and self.config["risk_management"]["take_profit"]["enabled"]:
            try:
                take_profit = signal["take_profit"]
                
                # Handle scaled take profit
                if isinstance(take_profit, list):
                    for level, amount_pct in zip(
                        take_profit,
                        self.config["risk_management"]["take_profit"]["scaled_amounts"]
                    ):
                        amount = order["amount"] * amount_pct
                        self.exchange.create_limit_sell_order(pair, amount, level)
                        logger.info(f"Created take profit for {pair} at {level} for {amount_pct*100}% of position")
                else:
                    self.exchange.create_limit_sell_order(pair, order["amount"], take_profit)
                    logger.info(f"Created take profit for {pair} at {take_profit}")
            except Exception as e:
                logger.error(f"Error creating take profit for {pair}: {str(e)}")
    
    def _daily_summary(self):
        """Generate and send daily performance summary."""
        try:
            # Get account info
            account_info = self.exchange.fetch_balance()
            
            # Calculate daily performance
            # (This is simplified - real implementation would compare to previous day)
            total_balance = account_info["total"]
            
            # Format the message
            message = "Daily Summary\n"
            message += "-------------\n"
            message += f"Total Balance: {total_balance}\n"
            message += f"Open Positions: {len(self.exchange.fetch_open_orders())}\n"
            
            # Send notification
            self.notification_manager.send_message(message)
            logger.info("Daily summary sent")
        except Exception as e:
            logger.error(f"Error generating daily summary: {str(e)}")
    
    def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")
        self.is_running = False
        
        # Cancel all schedules
        schedule.clear()
        
        # Clean up resources
        # (Exchange connection, database connections, etc.)
        
        # Notify stop
        self.notification_manager.send_message("Trading bot stopped")
        logger.info("Trading bot stopped")
    
    def _handle_exit(self, signum, frame):
        """Handle exit signals for clean shutdown."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="NuancedTrader - Advanced Cryptocurrency Trading Bot")
    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        default="src/config/config.yml"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    bot = TradingBot(config_path=args.config)
    bot.start() 