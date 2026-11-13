"""
Jinja template filters used across every page.

Templates can then write {{ product.cost_price|money }} or
{{ movement.created_at|timeago }} instead of formatting values inline.
"""

from datetime import datetime

from flask import current_app, g

from database.db import query


def currency_symbol():
    """Read the currency symbol from the settings table (cached per request)."""
    if "_currency_symbol" not in g:
        symbol = current_app.config["CURRENCY_SYMBOL"]
        try:
            row = query(
                "SELECT value FROM settings WHERE key = 'currency_symbol'",
                one=True,
            )
            if row and row["value"]:
                symbol = row["value"]
        except Exception:
            # If the settings table is unavailable, fall back to config.
            pass
        g._currency_symbol = symbol
    return g._currency_symbol


def _parse_datetime(value):
    """Turn a SQLite text timestamp into a datetime object."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def register_filters(app):
    """Attach every custom filter to the given Flask app."""

    @app.template_global("currency_symbol")
    def currency_symbol_global():
        """Expose the active currency symbol to templates and scripts."""
        return currency_symbol()

    @app.template_filter("money")
    def money(value):
        """1234.5 -> ₹1,234.50"""
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return f"{currency_symbol()}{amount:,.2f}"

    @app.template_filter("number")
    def number(value):
        """1234 -> 1,234"""
        try:
            return f"{int(value or 0):,}"
        except (TypeError, ValueError):
            return "0"

    @app.template_filter("datefmt")
    def datefmt(value, fmt="%d %b %Y"):
        parsed = _parse_datetime(value)
        return parsed.strftime(fmt) if parsed else "-"

    @app.template_filter("timefmt")
    def timefmt(value, fmt="%I:%M %p"):
        parsed = _parse_datetime(value)
        return parsed.strftime(fmt) if parsed else "-"

    @app.template_filter("timeago")
    def timeago(value):
        """'2 hours ago', 'Yesterday', '12 Nov 2026'..."""
        parsed = _parse_datetime(value)
        if not parsed:
            return "-"

        seconds = (datetime.now() - parsed).total_seconds()
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} min ago"
        if seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} hr ago"
        if seconds < 172800:
            return "Yesterday"
        if seconds < 604800:
            return f"{int(seconds // 86400)} days ago"
        return parsed.strftime("%d %b %Y")
