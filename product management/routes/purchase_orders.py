"""Procurement: purchase orders and receiving stock."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from database.db import execute, query
from utils.helpers import clean, next_po_number, parse_float, parse_int

purchase_orders_bp = Blueprint("purchase_orders", __name__, url_prefix="/purchase-orders")

STATUS_LABELS = {
    "draft": "Draft",
    "ordered": "Ordered",
    "received": "Received",
    "cancelled": "Cancelled",
}


@purchase_orders_bp.route("/")
def index():
    orders = query(
        """
        SELECT po.*, s.name AS supplier_name,
               (SELECT COUNT(*) FROM purchase_order_items i
                 WHERE i.purchase_order_id = po.id) AS item_count
        FROM purchase_orders po
        LEFT JOIN suppliers s ON s.id = po.supplier_id
        ORDER BY po.created_at DESC, po.id DESC
        """
    )
    return render_template(
        "purchase_orders/list.html",
        page_title="Purchase orders",
        active_page="purchase_orders",
        orders=orders,
        status_labels=STATUS_LABELS,
    )


@purchase_orders_bp.route("/new", methods=["GET", "POST"])
def create():
    suppliers = query("SELECT id, name FROM suppliers ORDER BY name COLLATE NOCASE")
    products = query(
        "SELECT id, name, sku, cost_price FROM products WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
    )

    form = {"supplier_id": "", "expected_date": "", "notes": ""}

    if request.method == "POST":
        form = {
            "supplier_id": clean(request.form.get("supplier_id")),
            "expected_date": clean(request.form.get("expected_date")),
            "notes": clean(request.form.get("notes")),
        }

        supplier = None
        if form["supplier_id"].isdigit():
            supplier = query(
                "SELECT id, name FROM suppliers WHERE id = ?",
                (int(form["supplier_id"]),),
                one=True,
            )

        items = []
        product_ids = request.form.getlist("product_id")
        quantities = request.form.getlist("quantity")
        costs = request.form.getlist("unit_cost")

        for product_id, quantity, cost in zip(product_ids, quantities, costs):
            if not product_id.isdigit():
                continue
            qty = parse_int(quantity)
            unit_cost = parse_float(cost)
            if qty <= 0:
                continue
            product = query(
                "SELECT id, name FROM products WHERE id = ? AND is_active = 1",
                (int(product_id),),
                one=True,
            )
            if product is None:
                continue
            items.append(
                {
                    "product_id": product["id"],
                    "name": product["name"],
                    "quantity": qty,
                    "unit_cost": unit_cost,
                    "line_total": qty * unit_cost,
                }
            )

        errors = []
        if supplier is None:
            errors.append("Choose a supplier.")
        if not items:
            errors.append("Add at least one product with a quantity above zero.")

        if not errors:
            po_number = next_po_number(
                "PO",
                lambda number: query(
                    "SELECT id FROM purchase_orders WHERE po_number = ?", (number,), one=True
                ),
            )
            total = sum(item["line_total"] for item in items)
            expected_date = form["expected_date"] if len(form["expected_date"]) == 10 else None

            order_id = execute(
                """
                INSERT INTO purchase_orders
                    (po_number, supplier_id, status, expected_date, total_amount, notes)
                VALUES (?, ?, 'draft', ?, ?, ?)
                """,
                (po_number, supplier["id"], expected_date, total, form["notes"] or None),
            )

            for item in items:
                execute(
                    """
                    INSERT INTO purchase_order_items
                        (purchase_order_id, product_id, quantity, unit_cost, line_total)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        item["product_id"],
                        item["quantity"],
                        item["unit_cost"],
                        item["line_total"],
                    ),
                )

            flash(f"Purchase order {po_number} created.", "success")
            return redirect(url_for("purchase_orders.detail", order_id=order_id))

        for error in errors:
            flash(error, "error")

    return render_template(
        "purchase_orders/form.html",
        page_title="New purchase order",
        active_page="purchase_orders",
        form=form,
        suppliers=suppliers,
        products=products,
    )


@purchase_orders_bp.route("/<int:order_id>")
def detail(order_id):
    order = query(
        """
        SELECT po.*, s.name AS supplier_name, s.contact_person, s.email, s.phone
        FROM purchase_orders po
        LEFT JOIN suppliers s ON s.id = po.supplier_id
        WHERE po.id = ?
        """,
        (order_id,),
        one=True,
    )
    if order is None:
        abort(404)

    items = query(
        """
        SELECT i.*, p.name AS product_name, p.sku, p.unit
        FROM purchase_order_items i
        JOIN products p ON p.id = i.product_id
        WHERE i.purchase_order_id = ?
        ORDER BY i.id
        """,
        (order_id,),
    )

    return render_template(
        "purchase_orders/detail.html",
        page_title=order["po_number"],
        active_page="purchase_orders",
        order=order,
        items=items,
        status_labels=STATUS_LABELS,
    )


@purchase_orders_bp.route("/<int:order_id>/status", methods=["POST"])
def update_status(order_id):
    order = query("SELECT * FROM purchase_orders WHERE id = ?", (order_id,), one=True)
    if order is None:
        abort(404)

    action = clean(request.form.get("action"))
    status = order["status"]

    if action == "order" and status == "draft":
        execute("UPDATE purchase_orders SET status = 'ordered' WHERE id = ?", (order_id,))
        flash(f"{order['po_number']} marked as ordered.", "success")

    elif action == "cancel" and status in ("draft", "ordered"):
        execute("UPDATE purchase_orders SET status = 'cancelled' WHERE id = ?", (order_id,))
        flash(f"{order['po_number']} cancelled.", "success")

    elif action == "receive" and status in ("draft", "ordered"):
        items = query(
            """
            SELECT i.*, p.name AS product_name, p.unit
            FROM purchase_order_items i
            JOIN products p ON p.id = i.product_id
            WHERE i.purchase_order_id = ?
            """,
            (order_id,),
        )

        if not items:
            flash("This purchase order has no items to receive.", "error")
            return redirect(url_for("purchase_orders.detail", order_id=order_id))

        for item in items:
            execute(
                """
                UPDATE products
                SET quantity = quantity + ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (item["quantity"], item["product_id"]),
            )
            execute(
                """
                INSERT INTO stock_movements
                    (product_id, movement_type, quantity, reference, note)
                VALUES (?, 'in', ?, ?, 'Received against purchase order')
                """,
                (item["product_id"], item["quantity"], order["po_number"]),
            )
            execute(
                """
                INSERT INTO transactions
                    (reference, type, product_id, quantity, unit_price, total_amount, note)
                VALUES (?, 'purchase', ?, ?, ?, ?, 'Purchase order received')
                """,
                (
                    order["po_number"],
                    item["product_id"],
                    item["quantity"],
                    item["unit_cost"],
                    item["line_total"],
                ),
            )

        execute("UPDATE purchase_orders SET status = 'received' WHERE id = ?", (order_id,))
        flash(f"{order['po_number']} received and stock updated.", "success")

    else:
        flash("That action is not available for this purchase order.", "error")

    return redirect(url_for("purchase_orders.detail", order_id=order_id))
