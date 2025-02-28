#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Notification Manager
------------------

This module provides notification functionality for the trading bot.
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from loguru import logger


class NotificationManager:
    """
    Notification manager for sending alerts and updates.
    
    Supports:
    - Email notifications
    - Telegram notifications
    - (Extendable for other notification channels)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the notification manager.
        
        Args:
            config: Notification configuration
        """
        self.config = config
        self.logger = logger.bind(module='NotificationManager')
        
        # Email configuration
        self.email_config = self.config.get('email', {})
        self.email_enabled = self.email_config.get('enabled', False)
        
        # Telegram configuration
        self.telegram_config = self.config.get('telegram', {})
        self.telegram_enabled = self.telegram_config.get('enabled', False)
        
        # Cache of recent messages to avoid duplicates
        self.recent_messages = []
        self.max_recent_messages = 10
        
        self.logger.info(f"Notification manager initialized (Email: {'enabled' if self.email_enabled else 'disabled'}, Telegram: {'enabled' if self.telegram_enabled else 'disabled'})")
    
    def send_message(self, message: str, subject: Optional[str] = None, 
                    level: str = 'info', attachment: Optional[str] = None) -> bool:
        """
        Send a notification message to all configured channels.
        
        Args:
            message: Message content
            subject: Message subject (for email)
            level: Message level ('info', 'warning', 'error', 'success')
            attachment: Path to attachment file (for email)
            
        Returns:
            True if message was sent to at least one channel, False otherwise
        """
        # Use default subject if not provided
        if subject is None:
            subject = f"Trading Bot {level.capitalize()} Notification"
        
        # Check for duplicate messages (avoid spam)
        if message in self.recent_messages:
            return True
        
        # Cache message
        self.recent_messages.append(message)
        if len(self.recent_messages) > self.max_recent_messages:
            self.recent_messages.pop(0)
        
        # Log the message
        log_fn = getattr(self.logger, level.lower(), self.logger.info)
        log_fn(f"Notification: {message}")
        
        # Send to all enabled channels
        sent = False
        
        if self.email_enabled:
            email_sent = self._send_email(message, subject, level, attachment)
            sent = sent or email_sent
        
        if self.telegram_enabled:
            telegram_sent = self._send_telegram(message, level)
            sent = sent or telegram_sent
        
        return sent
    
    def _send_email(self, message: str, subject: str, level: str,
                   attachment: Optional[str] = None) -> bool:
        """
        Send an email notification.
        
        Args:
            message: Message content
            subject: Email subject
            level: Message level
            attachment: Path to attachment file
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.email_enabled:
            return False
        
        try:
            # Get email config
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            sender_email = self.email_config.get('sender_email')
            receiver_email = self.email_config.get('receiver_email')
            password = os.getenv('EMAIL_PASSWORD')  # Get from environment variable
            
            # Check required fields
            if not all([smtp_server, smtp_port, sender_email, receiver_email]):
                self.logger.error("Missing required email configuration")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = subject
            
            # Format message with HTML
            email_message = f"""
            <html>
              <body>
                <h2>{subject}</h2>
                <pre>{message}</pre>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(email_message, 'html'))
            
            # Add attachment if provided
            if attachment and os.path.exists(attachment):
                with open(attachment, 'rb') as file:
                    attachment_data = file.read()
                    attachment_mime = MIMEText(attachment_data)
                    attachment_mime.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(attachment)}"')
                    msg.attach(attachment_mime)
            
            # Connect to server and send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if password:
                    server.login(sender_email, password)
                server.send_message(msg)
            
            self.logger.debug(f"Email notification sent to {receiver_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    def _send_telegram(self, message: str, level: str) -> bool:
        """
        Send a Telegram notification.
        
        Args:
            message: Message content
            level: Message level
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.telegram_enabled:
            return False
        
        try:
            # Get Telegram config
            bot_token = self.telegram_config.get('bot_token')
            chat_id = self.telegram_config.get('chat_id')
            
            # Check required fields
            if not all([bot_token, chat_id]):
                self.logger.error("Missing required Telegram configuration")
                return False
            
            # Add emoji based on level
            emoji_map = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'success': '✅'
            }
            emoji = emoji_map.get(level.lower(), 'ℹ️')
            
            # Format message
            formatted_message = f"{emoji} *{level.upper()}*\n```\n{message}\n```"
            
            # Send message
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            self.logger.debug(f"Telegram notification sent to chat {chat_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {str(e)}")
            return False
    
    def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """
        Send a notification for a trade.
        
        Args:
            trade_data: Trade information
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        # Extract trade details
        pair = trade_data.get('pair', 'Unknown')
        action = trade_data.get('action', 'Unknown')
        amount = trade_data.get('amount', 0)
        price = trade_data.get('price', 0)
        
        # Create message
        subject = f"Trade Executed: {action.upper()} {pair}"
        message = f"Trade Executed:\n"
        message += f"Pair: {pair}\n"
        message += f"Action: {action.upper()}\n"
        message += f"Amount: {amount}\n"
        
        if price:
            message += f"Price: {price}\n"
        
        if 'stop_loss' in trade_data:
            message += f"Stop Loss: {trade_data['stop_loss']}\n"
        
        if 'take_profit' in trade_data:
            if isinstance(trade_data['take_profit'], list):
                take_profit_str = ', '.join([str(tp) for tp in trade_data['take_profit']])
                message += f"Take Profit Levels: {take_profit_str}\n"
            else:
                message += f"Take Profit: {trade_data['take_profit']}\n"
        
        # Send as a success notification
        return self.send_message(message, subject, 'success')
    
    def send_error_notification(self, error_message: str, context: Optional[str] = None) -> bool:
        """
        Send an error notification.
        
        Args:
            error_message: Error message
            context: Context information
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        subject = "Trading Bot Error"
        message = f"Error occurred in the trading bot\n"
        
        if context:
            message += f"Context: {context}\n"
        
        message += f"Error: {error_message}\n"
        
        # Send as an error notification
        return self.send_message(message, subject, 'error')
    
    def send_performance_summary(self, performance_data: Dict[str, Any]) -> bool:
        """
        Send a performance summary notification.
        
        Args:
            performance_data: Performance metrics
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        subject = "Trading Bot Performance Summary"
        message = "Performance Summary:\n"
        
        # Format performance metrics
        for metric, value in performance_data.items():
            # Format as percentage if applicable
            if 'percent' in metric.lower() or 'rate' in metric.lower():
                message += f"{metric}: {value * 100:.2f}%\n"
            elif isinstance(value, float):
                message += f"{metric}: {value:.6f}\n"
            else:
                message += f"{metric}: {value}\n"
        
        # Send as an info notification
        return self.send_message(message, subject, 'info') 