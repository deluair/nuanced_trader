#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger Setup
-----------

This module configures the logging system for the trading bot.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logger(log_level: str = "INFO", log_to_file: bool = True, 
                 log_dir: Optional[str] = None) -> None:
    """
    Set up the logger for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file in addition to console
        log_dir: Directory to store log files (creates logs/ in project root if None)
    """
    # Remove default logger
    logger.remove()
    
    # Convert string log level to corresponding value
    log_levels = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    level = log_levels.get(log_level.upper(), 20)  # Default to INFO
    
    # Add console handler with colors
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Add file handler if requested
    if log_to_file:
        if log_dir is None:
            # Default to logs directory in project root
            log_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "logs"
            )
        
        # Create logs directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"trading_bot_{timestamp}.log")
        
        # Add file handler
        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",  # Rotate file when it reaches 10 MB
            retention="1 month",  # Keep logs for 1 month
            compression="zip"  # Compress rotated logs
        )
        
        logger.info(f"Logging to file: {log_file}")
    
    logger.info(f"Logger initialized with level {log_level}")


def get_logger_for_module(module_name: str) -> logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        Logger instance for the module
    """
    return logger.bind(module=module_name)


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.
    """
    
    @property
    def logger(self):
        """
        Get a logger instance for this class.
        
        Returns:
            Logger instance with class name context
        """
        return logger.bind(module=self.__class__.__name__) 