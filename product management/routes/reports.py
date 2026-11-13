"""Reports: inventory valuation and stock statistics."""

from flask import Blueprint, render_template

from database.db import query

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
def index():
    summary = {
        "product_count": query(
            "SELECT COUNT(*) FROM products WHERE is_active = 1", one=True
        )[0],
        "units": query(
            "SELECT COALESCE(SUM(quantity), 0) FROM products WHERE is_active = 1", one=True
        )[0],
        "cost_value": query(
            "SELECT COALESCE(SUM(quantity * cost_price), 0) FROM products WHERE is_active = 1",
            one=True,
        )[0],
        "retail_value": query(
            "SELECT COALESCE(SUM(quantity * selling_price), 0) FROM products WHERE is_active = 1",
            one=True,
        )[0],
        "low_stock": query(
            "SELECT COUNT(*) FROM products WHERE is_active = 1 AND quantity <= reorder_level",
            one=True,
        )[0],
        "supplier_count": query("SELECT COUNT(*) FROM suppliers", one=True)[0],
    }
    summary["potential_profit"] = summary["retail_value"] - summary["cost_value"]

    categories = query(
        """
        SELECT c.name,
               COUNT(p.id) AS product_count,
               COALESCE(SUM(p.quantity), 0) AS units,
               COALESCE(SUM(p.quantity * p.cost_price), 0) AS cost_value,
               COALESCE(SUM(p.quantity * p.selling_price), 0) AS retail_value
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.is_active = 1
        GROUP BY c.id
        ORDER BY cost_value DESC, c.name COLLATE NOCASE
        """
    )

    top_products = query(
        """
        SELECT p.name, p.sku, p.quantity, p.unit, p.cost_price,
               (p.quantity * p.cost_price) AS stock_value
        FROM products p
        WHERE p.is_active = 1
        ORDER BY stock_value DESC, p.name COLLATE NOCASE
        LIMIT 8
        """
    )

    low_stock = query(
        """
        SELECT p.name, p.sku, p.quantity, p.unit, p.reorder_level, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.is_active = 1 AND p.quantity <= p.reorder_level
        ORDER BY (p.quantity - p.reorder_level) ASC, p.name COLLATE NOCASE
        """
    )

    movements = {
        row["movement_type"]: {"count": row["count"], "units": row["units"]}
        for row in query(
            """
            SELECT movement_type, COUNT(*) AS count, COALESCE(SUM(quantity), 0) AS units
            FROM stock_movements
            WHERE date(created_at) >= date('now', 'localtime', '-30 day')
            GROUP BY movement_type
            """
        )
    }

    order_status = query(
        """
        SELECT status, COUNT(*) AS count, COALESCE(SUM(total_amount), 0) AS total
        FROM purchase_orders
        GROUP BY status
        """
    )

    return render_template(
        "reports/index.html",
        page_title="Reports",
        active_page="reports",
        summary=summary,
        categories=categories,
        top_products=top_products,
        low_stock=low_stock,
        movements=movements,
        order_status=order_status,
    )
