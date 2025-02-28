#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bot Status API Endpoint
----------------------

This module provides a RESTful API endpoint to monitor the status
of the trading bot. It returns information about the bot's operational
status, recent activities, and configuration.
"""

import json
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging
import os
import sys
import threading

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_loader import ConfigLoader

app = Flask(__name__, static_folder='../../docs')
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables to track bot status
bot_status = {
    "status": "offline",
    "last_active": None,
    "running_since": None,
    "mode": "unknown",
    "pairs": [],
    "activities": []
}

# Lock for thread-safe updates
status_lock = threading.Lock()


def initialize_status(config=None):
    """Initialize bot status with configuration data"""
    global bot_status
    
    try:
        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.get_config()
        
        with status_lock:
            bot_status["mode"] = "paper_trading" if config["exchange"]["paper_trading"] else "live_trading"
            bot_status["pairs"] = config["exchange"]["trading_pairs"]
    except Exception as e:
        logger.error(f"Error initializing status: {e}")


def update_bot_status(status="online"):
    """Update the bot's operational status"""
    global bot_status
    
    with status_lock:
        bot_status["status"] = status
        bot_status["last_active"] = datetime.now().isoformat()
        
        if status == "online" and bot_status["running_since"] is None:
            bot_status["running_since"] = datetime.now().isoformat()
        elif status == "offline":
            bot_status["running_since"] = None


def add_activity(message, activity_type="info"):
    """Add an activity to the bot's activity log"""
    global bot_status
    
    with status_lock:
        activity = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "type": activity_type
        }
        
        bot_status["activities"].insert(0, activity)
        
        # Keep only the last 50 activities
        if len(bot_status["activities"]) > 50:
            bot_status["activities"] = bot_status["activities"][:50]


@app.route('/api/status', methods=['GET'])
def get_status():
    """API endpoint to get the current bot status"""
    with status_lock:
        return jsonify(bot_status)


@app.route('/api/status/update', methods=['POST'])
def update_status():
    """API endpoint to update the bot status (for internal use)"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if "status" in data:
        update_bot_status(data["status"])
    
    if "activity" in data and "message" in data["activity"]:
        add_activity(
            data["activity"]["message"],
            data["activity"].get("type", "info")
        )
    
    return jsonify({"success": True})


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_docs(path):
    """Serve the documentation website"""
    if path == "" or path == "/":
        return send_from_directory(app.static_folder, 'index.html')
    return send_from_directory(app.static_folder, path)


def run_api_server(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask API server"""
    initialize_status()
    
    # Simulate some initial activity
    add_activity("API server started", "info")
    add_activity("Loading configuration", "info")
    add_activity("Initializing trading bot", "info")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_api_server(debug=True) 