# Nuanced Trader

![Nuanced Trader Logo](assets/images/logo.png)

An advanced cryptocurrency trading bot designed for sophisticated algorithmic trading strategies with a focus on risk management and adaptability to market conditions.

## Features

- **Multiple Trading Strategies**: Adaptive Momentum, Mean Reversion, Trend Following, and Machine Learning-based approaches
- **Advanced Risk Management**: Position sizing, stop-loss calculation, dynamic take-profit levels
- **Multi-Exchange Support**: Compatible with Coinbase, Binance, and other major exchanges
- **Real-time Market Analysis**: Technical indicators, market regime detection, volatility analysis
- **Paper Trading Mode**: Test strategies without risking real funds
- **Performance Metrics**: Comprehensive analytics including Sharpe ratio, drawdown, win rate
- **Notifications**: Email and Telegram alerts for trades and system events

## Getting Started

### Prerequisites

- Python 3.8+
- Access to cryptocurrency exchange API (Coinbase, Binance, etc.)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/deluair/nuanced_trader.git
   cd nuanced_trader
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your settings:
   ```bash
   cp config.example.yml config.yml
   # Edit config.yml with your preferred settings and API keys
   ```

4. Run the bot:
   ```bash
   python src/main.py
   ```

## Configuration

The `config.yml` file contains all the configuration options:

```yaml
general:
  log_level: INFO
  data_directory: data
  cache_data: true
  backtesting_mode: false
  dry_run: true  # Set to false for live trading

exchange:
  name: coinbase  # or binance, kraken, etc.
  paper_trading: true  # Set to false for live trading
  api_key_env: EXCHANGE_API_KEY
  api_secret_env: EXCHANGE_API_SECRET
  trading_pairs: ["BTC/USD", "ETH/USD"]
  timeframe: 1h

# Additional configuration options...
```

## Safety First

- **Start with Paper Trading**: Always test your strategies with paper trading before using real funds
- **Use API Keys with Limited Permissions**: Trading-only permissions, no withdrawal access
- **Set Conservative Risk Parameters**: Limit per-trade and total account risk
- **Monitor Regularly**: Check the bot's performance and adjust as needed

## Backtesting

To test a strategy against historical data:

```bash
python src/main.py --backtest
```

To optimize strategy parameters:

```bash
python src/main.py --backtest --optimize
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

Trading cryptocurrencies involves significant risk. This software is for educational and research purposes only. Use at your own risk. 