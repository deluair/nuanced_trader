import numpy as np
import pandas as pd
from typing import List, Dict, Union, Optional
from datetime import datetime

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0, annualization_factor: int = 252) -> float:
    """
    Calculate the Sharpe ratio of a series of returns
    
    Args:
        returns: List of period returns (daily, weekly, etc.)
        risk_free_rate: Risk-free rate expressed in the same period as returns
        annualization_factor: Factor to annualize the returns (252 trading days, 52 weeks, 12 months)
    
    Returns:
        Sharpe ratio (annualized)
    """
    if not returns or len(returns) < 2:
        return 0.0
        
    returns_array = np.array(returns)
    
    # Calculate mean and standard deviation
    mean_return = np.mean(returns_array)
    std_return = np.std(returns_array, ddof=1)  # Sample standard deviation
    
    if std_return == 0:
        return 0.0
        
    # Calculate daily Sharpe ratio
    daily_sharpe = (mean_return - risk_free_rate) / std_return
    
    # Annualize
    return daily_sharpe * np.sqrt(annualization_factor)


def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.0, annualization_factor: int = 252) -> float:
    """
    Calculate the Sortino ratio of a series of returns (uses downside deviation instead of standard deviation)
    
    Args:
        returns: List of period returns (daily, weekly, etc.)
        risk_free_rate: Risk-free rate expressed in the same period as returns
        annualization_factor: Factor to annualize the returns (252 trading days, 52 weeks, 12 months)
    
    Returns:
        Sortino ratio (annualized)
    """
    if not returns or len(returns) < 2:
        return 0.0
        
    returns_array = np.array(returns)
    
    # Calculate mean
    mean_return = np.mean(returns_array)
    
    # Calculate downside deviation (standard deviation of negative returns only)
    downside_returns = returns_array[returns_array < 0]
    
    if len(downside_returns) == 0:
        return float('inf')  # Perfect score if no negative returns
        
    downside_deviation = np.std(downside_returns, ddof=1)
    
    if downside_deviation == 0:
        return 0.0
        
    # Calculate daily Sortino ratio
    daily_sortino = (mean_return - risk_free_rate) / downside_deviation
    
    # Annualize
    return daily_sortino * np.sqrt(annualization_factor)


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    Calculate the maximum drawdown from an equity curve
    
    Args:
        equity_curve: List of equity values over time
    
    Returns:
        Maximum drawdown as a percentage (0 to 1)
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
        
    # Calculate the running maximum and drawdowns
    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (running_max - equity_curve) / running_max
    
    # Return the maximum drawdown
    return np.max(drawdowns) if drawdowns.size > 0 else 0.0


def calculate_win_rate(trades: List[Dict]) -> float:
    """
    Calculate the win rate from a list of trades
    
    Args:
        trades: List of trade dictionaries with at least a 'profit_loss' key
    
    Returns:
        Win rate as a percentage (0 to 1)
    """
    if not trades:
        return 0.0
        
    winning_trades = sum(1 for trade in trades if trade.get('profit_loss', 0) > 0)
    total_trades = len(trades)
    
    return winning_trades / total_trades if total_trades > 0 else 0.0


def calculate_profit_factor(trades: List[Dict]) -> float:
    """
    Calculate the profit factor from a list of trades (gross profits / gross losses)
    
    Args:
        trades: List of trade dictionaries with at least a 'profit_loss' key
    
    Returns:
        Profit factor (> 1 is profitable)
    """
    if not trades:
        return 0.0
        
    gross_profits = sum(trade.get('profit_loss', 0) for trade in trades if trade.get('profit_loss', 0) > 0)
    gross_losses = sum(abs(trade.get('profit_loss', 0)) for trade in trades if trade.get('profit_loss', 0) < 0)
    
    return gross_profits / gross_losses if gross_losses > 0 else float('inf')


def calculate_average_trade(trades: List[Dict]) -> Dict[str, float]:
    """
    Calculate average trade metrics
    
    Args:
        trades: List of trade dictionaries with at least a 'profit_loss' key
    
    Returns:
        Dictionary with average profit, average win, average loss, and average holding time
    """
    if not trades:
        return {
            'avg_profit': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'avg_holding_time_hours': 0.0
        }
        
    # Calculate average profit/loss
    profits = [trade.get('profit_loss', 0) for trade in trades]
    avg_profit = np.mean(profits) if profits else 0.0
    
    # Calculate average win
    winning_trades = [trade.get('profit_loss', 0) for trade in trades if trade.get('profit_loss', 0) > 0]
    avg_win = np.mean(winning_trades) if winning_trades else 0.0
    
    # Calculate average loss
    losing_trades = [trade.get('profit_loss', 0) for trade in trades if trade.get('profit_loss', 0) < 0]
    avg_loss = np.mean(losing_trades) if losing_trades else 0.0
    
    # Calculate average holding time (if entry_time and exit_time are available)
    holding_times = []
    for trade in trades:
        if trade.get('entry_time') and trade.get('exit_time'):
            entry_time = pd.to_datetime(trade['entry_time'])
            exit_time = pd.to_datetime(trade['exit_time'])
            holding_time = (exit_time - entry_time).total_seconds() / 3600  # Convert to hours
            holding_times.append(holding_time)
    
    avg_holding_time = np.mean(holding_times) if holding_times else 0.0
    
    return {
        'avg_profit': float(avg_profit),
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'avg_holding_time_hours': float(avg_holding_time)
    }


def calculate_expectancy(trades: List[Dict]) -> float:
    """
    Calculate the expectancy (expected return per trade) from a list of trades
    
    Args:
        trades: List of trade dictionaries with at least a 'profit_loss' key
    
    Returns:
        Expectancy value
    """
    if not trades:
        return 0.0
        
    win_rate = calculate_win_rate(trades)
    
    # Calculate average win and loss
    winning_trades = [trade.get('profit_loss', 0) for trade in trades if trade.get('profit_loss', 0) > 0]
    losing_trades = [trade.get('profit_loss', 0) for trade in trades if trade.get('profit_loss', 0) < 0]
    
    avg_win = np.mean(winning_trades) if winning_trades else 0.0
    avg_loss = np.mean(losing_trades) if losing_trades else 0.0
    
    # Calculate R-ratio (average win / average loss)
    r_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # Calculate expectancy
    expectancy = (win_rate * r_ratio) - (1 - win_rate)
    
    return float(expectancy)


def calculate_annual_returns(equity_curve: List[float], dates: List[datetime]) -> Dict[int, float]:
    """
    Calculate annual returns from an equity curve
    
    Args:
        equity_curve: List of equity values over time
        dates: List of dates corresponding to each equity value
    
    Returns:
        Dictionary mapping years to annual returns
    """
    if not equity_curve or len(equity_curve) < 2 or len(equity_curve) != len(dates):
        return {}
        
    # Convert dates to pandas DatetimeIndex
    dates_index = pd.DatetimeIndex(dates)
    
    # Create a Series with equity values indexed by date
    equity_series = pd.Series(equity_curve, index=dates_index)
    
    # Resample to get year-end values
    annual_equity = equity_series.resample('Y').last()
    
    # Calculate year-over-year returns
    annual_returns = {}
    for year in range(annual_equity.index.year.min(), annual_equity.index.year.max() + 1):
        # Get equity value at the end of current and previous year
        current_year = annual_equity.get(str(year), None)
        prev_year = annual_equity.get(str(year-1), None)
        
        # If we have both values, calculate return
        if current_year is not None and prev_year is not None and prev_year > 0:
            annual_return = (current_year / prev_year) - 1
            annual_returns[year] = float(annual_return)
    
    return annual_returns


def generate_performance_summary(trades: List[Dict], equity_curve: List[float], 
                               dates: Optional[List[datetime]] = None) -> Dict:
    """
    Generate a comprehensive performance summary from trades and equity curve
    
    Args:
        trades: List of trade dictionaries
        equity_curve: List of equity values over time
        dates: Optional list of dates corresponding to equity values
    
    Returns:
        Dictionary with performance metrics
    """
    if not trades or not equity_curve:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'expectancy': 0.0,
            'total_return': 0.0
        }
    
    # Calculate basic trade metrics
    total_trades = len(trades)
    win_rate = calculate_win_rate(trades)
    profit_factor = calculate_profit_factor(trades)
    
    # Calculate returns from equity curve
    if len(equity_curve) >= 2:
        total_return = (equity_curve[-1] / equity_curve[0]) - 1
    else:
        total_return = 0.0
    
    # Calculate max drawdown
    max_drawdown = calculate_max_drawdown(equity_curve)
    
    # Generate returns from equity curve
    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] > 0:
            returns.append((equity_curve[i] / equity_curve[i-1]) - 1)
    
    # Calculate risk-adjusted metrics
    sharpe_ratio = calculate_sharpe_ratio(returns) if returns else 0.0
    sortino_ratio = calculate_sortino_ratio(returns) if returns else 0.0
    
    # Calculate average trade metrics
    avg_metrics = calculate_average_trade(trades)
    
    # Calculate expectancy
    expectancy = calculate_expectancy(trades)
    
    # Calculate annualized metrics
    cagr = (equity_curve[-1] / equity_curve[0]) ** (252 / len(equity_curve)) - 1 if len(equity_curve) > 1 else 0.0
    
    # Create and return the summary
    summary = {
        'total_trades': total_trades,
        'winning_trades': sum(1 for trade in trades if trade.get('profit_loss', 0) > 0),
        'losing_trades': sum(1 for trade in trades if trade.get('profit_loss', 0) < 0),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'cagr': cagr,
        'cagr_pct': cagr * 100,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown * 100,
        'avg_profit': avg_metrics['avg_profit'],
        'avg_win': avg_metrics['avg_win'],
        'avg_loss': avg_metrics['avg_loss'],
        'avg_holding_time_hours': avg_metrics['avg_holding_time_hours'],
        'expectancy': expectancy
    }
    
    # Add annual returns if dates are provided
    if dates and len(dates) == len(equity_curve):
        summary['annual_returns'] = calculate_annual_returns(equity_curve, dates)
    
    return summary 