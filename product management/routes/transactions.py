"""Transaction history: a read-only log of purchases, sales and stock updates."""

from flask import Blueprint, render_template, request

from database.db import query
from utils.helpers import clean

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")

TYPES = {
    "purchase": "Purchase",
    "sale": "Sale",
    "stock_in": "Stock in",
    "stock_out": "Stock out",
    "adjustment": "Adjustment",
}


@transactions_bp.route("/")
def index():
    type_filter = clean(request.args.get("type"))
    search = clean(request.args.get("q"))

    sql = """
        SELECT t.*, p.name AS product_name, p.sku
        FROM transactions t
        LEFT JOIN products p ON p.id = t.product_id
        WHERE 1 = 1
    """
    params = []

    if type_filter in TYPES:
        sql += " AND t.type = ?"
        params.append(type_filter)
    if search:
        sql += " AND (p.name LIKE ? OR t.reference LIKE ? OR t.note LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    sql += " ORDER BY t.created_at DESC, t.id DESC LIMIT 300"

    return render_template(
        "transactions/list.html",
        page_title="Transactions",
        active_page="transactions",
        transactions=query(sql, params),
        types=TYPES,
        type_filter=type_filter,
        search=search,
    )
