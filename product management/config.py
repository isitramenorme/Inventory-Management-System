"""
Application configuration.

All settings live in one place so the app is easy to move, re-brand or
deploy to another machine without hunting through the codebase.
"""

import os

# Absolute path of this file's folder -> the project root.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration used by the Flask application."""

    # --- Core Flask settings ---------------------------------------------
    # In production, set the SECRET_KEY environment variable instead.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # --- Branding ---------------------------------------------------------
    APP_NAME = "StockFlow"
    APP_TAGLINE = "Inventory Suite"
    APP_VERSION = "1.0.0"

    # --- Database ---------------------------------------------------------
    # SQLite file location. The folder is created automatically on start-up.
    DATABASE = os.path.join(BASE_DIR, "instance", "inventory.db")

    # --- Currency / display ----------------------------------------------
    # This is only the fallback. The value stored in the `settings` table
    # (editable from the app later) takes priority.
    CURRENCY_SYMBOL = "\u20b9"  # Indian Rupee

    # How many rows to show in dashboard tables.
    DASHBOARD_ROW_LIMIT = 5

    # Number of days plotted on the stock movement chart.
    CHART_DAYS = 7
