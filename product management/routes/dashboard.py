"""
Dashboard blueprint.

Stage 1 only reads data (there is nothing to write yet), but the queries
are written against the final schema so they keep working unchanged once
the product, stock and procurement modules are added.
"""

from collections import OrderedDict
from datetime import date, timedelta

from flask import Blueprint, current_app, render_template

from database.db import query

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard():
    """Render the main overview page."""

    # --- Headline numbers ------------------------------------------------
    total_products = query(
        "SELECT COUNT(*) FROM products WHERE is_active = 1", one=True
    )[0]
    units_in_stock = query(
        "SELECT COALESCE(SUM(quantity), 0) FROM products WHERE is_active = 1",
        one=True,
    )[0]
    low_stock_count = query(
        """
        SELECT COUNT(*) FROM products
        WHERE is_active = 1 AND quantity <= reorder_level
        """,
        one=True,
    )[0]
    inventory_value = query(
        """
        SELECT COALESCE(SUM(quantity * cost_price), 0)
        FROM products WHERE is_active = 1
        """,
        one=True,
    )[0]

    category_count = query("SELECT COUNT(*) FROM categories", one=True)[0]
    supplier_count = query("SELECT COUNT(*) FROM suppliers", one=True)[0]
    open_orders = query(
        "SELECT COUNT(*) FROM purchase_orders WHERE status IN ('draft', 'ordered')",
        one=True,
    )[0]

    stats = {
        "total_products": total_products,
        "units_in_stock": units_in_stock,
        "low_stock_count": low_stock_count,
        "inventory_value": inventory_value,
        "category_count": category_count,
        "supplier_count": supplier_count,
    }

    # --- Low stock alerts ------------------------------------------------
    low_stock_products = query(
        """
        SELECT p.id, p.name, p.sku, p.quantity, p.reorder_level, p.unit,
               c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.is_active = 1 AND p.quantity <= p.reorder_level
        ORDER BY (p.quantity - p.reorder_level) ASC, p.name ASC
        LIMIT ?
        """,
        (current_app.config["DASHBOARD_ROW_LIMIT"],),
    )

    # --- Recent stock movements ------------------------------------------
    recent_movements = query(
        """
        SELECT m.id, m.movement_type, m.quantity, m.reference, m.note,
               m.created_at, p.name AS product_name, p.sku
        FROM stock_movements m
        JOIN products p ON p.id = m.product_id
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT ?
        """,
        (current_app.config["DASHBOARD_ROW_LIMIT"],),
    )

    # --- Inventory value grouped by category ----------------------------
    category_rows = query(
        """
        SELECT c.id, c.name,
               COUNT(p.id) AS product_count,
               COALESCE(SUM(p.quantity * p.cost_price), 0) AS stock_value
        FROM categories c
        LEFT JOIN products p
               ON p.category_id = c.id AND p.is_active = 1
        GROUP BY c.id
        ORDER BY stock_value DESC, c.name ASC
        LIMIT 5
        """
    )

    categories = []
    for row in category_rows:
        share = (row["stock_value"] / inventory_value * 100) if inventory_value else 0
        categories.append(
            {
                "name": row["name"],
                "product_count": row["product_count"],
                "stock_value": row["stock_value"],
                "share": round(share, 1),
            }
        )

    # --- Seven day stock movement chart ---------------------------------
    chart = _movement_chart(current_app.config["CHART_DAYS"])

    return render_template(
        "dashboard.html",
        page_title="Dashboard",
        active_page="dashboard",
        stats=stats,
        low_stock_products=low_stock_products,
        recent_movements=recent_movements,
        categories=categories,
        chart=chart,
        open_orders=open_orders,
    )


def _movement_chart(days):
    """Build the per-day 'stock in' vs 'stock out' series for the chart."""
    start_day = date.today() - timedelta(days=days - 1)

    rows = query(
        """
        SELECT date(created_at) AS day,
               movement_type,
               SUM(quantity) AS total
        FROM stock_movements
        WHERE movement_type IN ('in', 'out')
          AND date(created_at) >= ?
        GROUP BY day, movement_type
        """,
        (start_day.isoformat(),),
    )

    totals = {}
    for row in rows:
        bucket = totals.setdefault(row["day"], {"in": 0, "out": 0})
        bucket[row["movement_type"]] = row["total"] or 0

    # One bucket per day, even when nothing happened that day.
    series = OrderedDict()
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        values = totals.get(day.isoformat(), {"in": 0, "out": 0})
        series[day] = values

    peak = max([max(v["in"], v["out"]) for v in series.values()] or [0])

    bars = []
    for day, values in series.items():
        bars.append(
            {
                "label": day.strftime("%a"),
                "full_date": day.strftime("%d %b %Y"),
                "in": values["in"],
                "out": values["out"],
                "in_pct": round(values["in"] / peak * 100) if peak else 0,
                "out_pct": round(values["out"] / peak * 100) if peak else 0,
            }
        )

    return {
        "bars": bars,
        "total_in": sum(v["in"] for v in series.values()),
        "total_out": sum(v["out"] for v in series.values()),
        "has_data": peak > 0,
    }
