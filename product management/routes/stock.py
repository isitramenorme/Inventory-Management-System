"""Stock management: movement history and recording stock changes."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from database.db import execute, query
from utils.helpers import clean, parse_int

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")

MOVEMENT_TYPES = ("in", "out", "adjustment")
OUT_REASONS = {
    "sale": "Sale",
    "damaged": "Damaged / lost",
    "supplier_return": "Returned to supplier",
    "other": "Other",
}


@stock_bp.route("/")
def index():
    product_id = clean(request.args.get("product"))
    movement_type = clean(request.args.get("type"))

    sql = """
        SELECT m.*, p.name AS product_name, p.sku, p.unit
        FROM stock_movements m
        JOIN products p ON p.id = m.product_id
        WHERE 1 = 1
    """
    params = []

    if product_id.isdigit():
        sql += " AND m.product_id = ?"
        params.append(int(product_id))
    if movement_type in MOVEMENT_TYPES:
        sql += " AND m.movement_type = ?"
        params.append(movement_type)

    sql += " ORDER BY m.created_at DESC, m.id DESC LIMIT 300"

    return render_template(
        "stock/list.html",
        page_title="Stock movements",
        active_page="stock",
        movements=query(sql, params),
        products=query("SELECT id, name, sku FROM products WHERE is_active = 1 ORDER BY name COLLATE NOCASE"),
        product_id=product_id,
        movement_type=movement_type,
        totals={
            "in": query(
                "SELECT COALESCE(SUM(quantity), 0) FROM stock_movements WHERE movement_type = 'in'",
                one=True,
            )[0],
            "out": query(
                "SELECT COALESCE(SUM(quantity), 0) FROM stock_movements WHERE movement_type = 'out'",
                one=True,
            )[0],
        },
    )


@stock_bp.route("/new", methods=["GET", "POST"])
def create():
    products = query(
        "SELECT id, name, sku, quantity, unit FROM products WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
    )

    form = {
        "product_id": clean(request.args.get("product")),
        "movement_type": "in",
        "quantity": "",
        "reason": "sale",
        "reference": "",
        "note": "",
    }

    if request.method == "POST":
        form = {
            "product_id": clean(request.form.get("product_id")),
            "movement_type": clean(request.form.get("movement_type")),
            "quantity": clean(request.form.get("quantity")),
            "reason": clean(request.form.get("reason"), "other"),
            "reference": clean(request.form.get("reference")),
            "note": clean(request.form.get("note")),
        }

        product = None
        if form["product_id"].isdigit():
            product = query(
                "SELECT * FROM products WHERE id = ? AND is_active = 1",
                (int(form["product_id"]),),
                one=True,
            )

        quantity = parse_int(form["quantity"])
        errors = []

        if product is None:
            errors.append("Choose a valid product.")
        if form["movement_type"] not in MOVEMENT_TYPES:
            errors.append("Choose a valid movement type.")
        if quantity < 0:
            errors.append("Quantity cannot be negative.")
        if form["movement_type"] != "adjustment" and quantity <= 0:
            errors.append("Quantity must be greater than zero.")
        if (
            product is not None
            and form["movement_type"] == "out"
            and quantity > product["quantity"]
        ):
            errors.append(f"Only {product['quantity']} {product['unit']} in stock.")

        if not errors:
            if form["movement_type"] == "adjustment":
                difference = quantity - product["quantity"]
                if difference == 0:
                    flash("Counted quantity matches the current stock. Nothing to adjust.", "info")
                    return redirect(url_for("stock.index"))

                new_quantity = quantity
                movement_quantity = abs(difference)
                transaction_quantity = difference
                transaction_type = "adjustment"
                note = form["note"] or f"Stocktake: {product['quantity']} \u2192 {quantity}"
                unit_price = product["cost_price"]
            elif form["movement_type"] == "in":
                difference = quantity
                new_quantity = product["quantity"] + quantity
                movement_quantity = quantity
                transaction_quantity = quantity
                transaction_type = "stock_in"
                note = form["note"]
                unit_price = product["cost_price"]
            else:
                difference = -quantity
                new_quantity = product["quantity"] - quantity
                movement_quantity = quantity
                transaction_quantity = -quantity
                transaction_type = "sale" if form["reason"] == "sale" else "stock_out"
                note = form["note"]
                if form["reason"] != "sale":
                    reason_label = OUT_REASONS.get(form["reason"], "Other")
                    note = f"{reason_label}. {note}".strip()
                unit_price = product["selling_price"]

            execute(
                "UPDATE products SET quantity = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (new_quantity, product["id"]),
            )
            execute(
                """
                INSERT INTO stock_movements
                    (product_id, movement_type, quantity, reference, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    product["id"],
                    form["movement_type"],
                    movement_quantity,
                    form["reference"] or None,
                    note or None,
                ),
            )
            execute(
                """
                INSERT INTO transactions
                    (reference, type, product_id, quantity, unit_price, total_amount, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form["reference"] or None,
                    transaction_type,
                    product["id"],
                    transaction_quantity,
                    unit_price,
                    abs(transaction_quantity) * unit_price,
                    note or None,
                ),
            )

            flash(f"Stock updated for \u201c{product['name']}\u201d.", "success")
            return redirect(url_for("stock.index"))

        for error in errors:
            flash(error, "error")

    return render_template(
        "stock/form.html",
        page_title="Record movement",
        active_page="stock",
        form=form,
        products=products,
        out_reasons=OUT_REASONS,
    )
