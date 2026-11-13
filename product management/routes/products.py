"""Product management: list, create, edit and delete products."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from database.db import execute, query
from utils.helpers import clean, parse_float, parse_int

products_bp = Blueprint("products", __name__, url_prefix="/products")

FORM_FIELDS = (
    "sku",
    "name",
    "description",
    "category_id",
    "supplier_id",
    "unit",
    "cost_price",
    "selling_price",
    "quantity",
    "reorder_level",
)


def _form_options():
    return {
        "categories": query("SELECT id, name FROM categories ORDER BY name COLLATE NOCASE"),
        "suppliers": query("SELECT id, name FROM suppliers ORDER BY name COLLATE NOCASE"),
    }


@products_bp.route("/")
def index():
    search = clean(request.args.get("q"))
    category_id = clean(request.args.get("category"))
    stock_filter = clean(request.args.get("stock"))

    sql = """
        SELECT p.*, c.name AS category_name, s.name AS supplier_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        WHERE p.is_active = 1
    """
    params = []

    if search:
        sql += " AND (p.name LIKE ? OR p.sku LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category_id.isdigit():
        sql += " AND p.category_id = ?"
        params.append(int(category_id))
    if stock_filter == "low":
        sql += " AND p.quantity <= p.reorder_level"
    elif stock_filter == "out":
        sql += " AND p.quantity = 0"

    sql += " ORDER BY p.name COLLATE NOCASE"

    return render_template(
        "products/list.html",
        page_title="Products",
        active_page="products",
        products=query(sql, params),
        categories=query("SELECT id, name FROM categories ORDER BY name COLLATE NOCASE"),
        search=search,
        category_id=category_id,
        stock_filter=stock_filter,
    )


@products_bp.route("/new", methods=["GET", "POST"])
def create():
    form = {
        "sku": "",
        "name": "",
        "description": "",
        "category_id": "",
        "supplier_id": "",
        "unit": "pcs",
        "cost_price": "0",
        "selling_price": "0",
        "quantity": "0",
        "reorder_level": "0",
    }

    if request.method == "POST":
        form = {field: clean(request.form.get(field)) for field in FORM_FIELDS}
        errors = []

        if not form["name"]:
            errors.append("Product name is required.")
        if not form["sku"]:
            errors.append("SKU is required.")
        elif query("SELECT id FROM products WHERE sku = ?", (form["sku"],), one=True):
            errors.append("That SKU is already in use.")

        cost = parse_float(form["cost_price"])
        selling = parse_float(form["selling_price"])
        quantity = parse_int(form["quantity"])
        reorder = parse_int(form["reorder_level"])

        if cost < 0 or selling < 0:
            errors.append("Prices cannot be negative.")
        if quantity < 0 or reorder < 0:
            errors.append("Stock quantities cannot be negative.")

        if not errors:
            product_id = execute(
                """
                INSERT INTO products
                    (sku, name, description, category_id, supplier_id, unit,
                     cost_price, selling_price, quantity, reorder_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form["sku"],
                    form["name"],
                    form["description"] or None,
                    int(form["category_id"]) if form["category_id"].isdigit() else None,
                    int(form["supplier_id"]) if form["supplier_id"].isdigit() else None,
                    form["unit"] or "pcs",
                    cost,
                    selling,
                    quantity,
                    reorder,
                ),
            )

            if quantity > 0:
                execute(
                    """
                    INSERT INTO stock_movements
                        (product_id, movement_type, quantity, reference, note)
                    VALUES (?, 'in', ?, 'OPENING', 'Opening stock')
                    """,
                    (product_id, quantity),
                )
                execute(
                    """
                    INSERT INTO transactions
                        (reference, type, product_id, quantity, unit_price, total_amount, note)
                    VALUES ('OPENING', 'stock_in', ?, ?, ?, ?, 'Opening stock')
                    """,
                    (product_id, quantity, cost, quantity * cost),
                )

            flash(f"Product \u201c{form['name']}\u201d added.", "success")
            return redirect(url_for("products.index"))

        for error in errors:
            flash(error, "error")

    return render_template(
        "products/form.html",
        page_title="Add product",
        active_page="products",
        mode="create",
        form=form,
        **_form_options(),
    )


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
def edit(product_id):
    product = query("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if product is None:
        abort(404)

    form = {field: "" if product[field] is None else str(product[field]) for field in FORM_FIELDS}

    if request.method == "POST":
        form = {field: clean(request.form.get(field)) for field in FORM_FIELDS}
        errors = []

        if not form["name"]:
            errors.append("Product name is required.")
        if not form["sku"]:
            errors.append("SKU is required.")
        elif query(
            "SELECT id FROM products WHERE sku = ? AND id <> ?",
            (form["sku"], product_id),
            one=True,
        ):
            errors.append("That SKU is already in use.")

        cost = parse_float(form["cost_price"])
        selling = parse_float(form["selling_price"])
        reorder = parse_int(form["reorder_level"])

        if cost < 0 or selling < 0:
            errors.append("Prices cannot be negative.")
        if reorder < 0:
            errors.append("Reorder level cannot be negative.")

        if not errors:
            execute(
                """
                UPDATE products
                SET sku = ?, name = ?, description = ?, category_id = ?,
                    supplier_id = ?, unit = ?, cost_price = ?, selling_price = ?,
                    reorder_level = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (
                    form["sku"],
                    form["name"],
                    form["description"] or None,
                    int(form["category_id"]) if form["category_id"].isdigit() else None,
                    int(form["supplier_id"]) if form["supplier_id"].isdigit() else None,
                    form["unit"] or "pcs",
                    cost,
                    selling,
                    reorder,
                    product_id,
                ),
            )
            flash("Product updated.", "success")
            return redirect(url_for("products.index"))

        for error in errors:
            flash(error, "error")

    return render_template(
        "products/form.html",
        page_title="Edit product",
        active_page="products",
        mode="edit",
        product=product,
        form=form,
        **_form_options(),
    )


@products_bp.route("/<int:product_id>/delete", methods=["POST"])
def delete(product_id):
    product = query("SELECT name FROM products WHERE id = ?", (product_id,), one=True)
    if product is None:
        abort(404)

    # Archive instead of hard-deleting: stock history and purchase orders stay
    # intact, while the product disappears from the catalogue.
    execute(
        """
        UPDATE products
        SET is_active = 0, updated_at = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (product_id,),
    )
    flash(f"Product \u201c{product['name']}\u201d deleted.", "success")
    return redirect(url_for("products.index"))
