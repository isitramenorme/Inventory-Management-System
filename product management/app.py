"""
StockFlow - Inventory & Stock Management System
===============================================

Stage 1: project structure, Flask configuration, SQLite initialisation
and the shared application layout (sidebar + top bar + dashboard shell).

Run with:
    python app.py

Then open http://127.0.0.1:5000
"""

import os
from datetime import datetime

from flask import Flask, render_template

from config import Config
from database.db import init_app, init_db
from routes.categories import categories_bp
from routes.dashboard import dashboard_bp
from routes.products import products_bp
from routes.purchase_orders import purchase_orders_bp
from routes.reports import reports_bp
from routes.stock import stock_bp
from routes.suppliers import suppliers_bp
from routes.transactions import transactions_bp
from utils.filters import register_filters


def create_app(config_class=Config):
    """Application factory: builds and configures the Flask app."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Make sure the instance folder (which holds the SQLite file) exists.
    os.makedirs(app.instance_path, exist_ok=True)

    # --- Database ---------------------------------------------------------
    # Registers the connection teardown hook, then creates any missing
    # tables. `CREATE TABLE IF NOT EXISTS` makes this safe on every start.
    init_app(app)
    with app.app_context():
        init_db()

    # --- Template helpers (money / date formatting) -----------------------
    register_filters(app)

    # --- Routes -----------------------------------------------------------
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(purchase_orders_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(reports_bp)

    # --- Values available to every template --------------------------------
    @app.context_processor
    def inject_globals():
        return {"today": datetime.now()}

    # --- Error pages ------------------------------------------------------
    @app.errorhandler(404)
    def page_not_found(error):
        return (
            render_template(
                "errors/404.html",
                page_title="Page not found",
                active_page="",
            ),
            404,
        )

    @app.errorhandler(500)
    def server_error(error):
        return (
            render_template(
                "errors/500.html",
                page_title="Something went wrong",
                active_page="",
            ),
            500,
        )

    return app


app = create_app()


if __name__ == "__main__":
    # debug=True gives auto-reload while developing. Turn it off before
    # sharing the app with real users.
    app.run(host="127.0.0.1", port=5000, debug=True)
