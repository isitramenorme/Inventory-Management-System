"""Supplier management: list, create, edit and delete suppliers."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from database.db import execute, query
from utils.helpers import clean

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/suppliers")

FIELDS = ("name", "contact_person", "email", "phone", "address")


@suppliers_bp.route("/")
def index():
    suppliers = query(
        """
        SELECT s.*,
               COUNT(DISTINCT p.id) AS product_count,
               COUNT(DISTINCT po.id) AS order_count
        FROM suppliers s
        LEFT JOIN products p ON p.supplier_id = s.id AND p.is_active = 1
        LEFT JOIN purchase_orders po ON po.supplier_id = s.id
        GROUP BY s.id
        ORDER BY s.name COLLATE NOCASE
        """
    )
    return render_template(
        "suppliers/list.html",
        page_title="Suppliers",
        active_page="suppliers",
        suppliers=suppliers,
    )


@suppliers_bp.route("/new", methods=["GET", "POST"])
def create():
    form = {field: "" for field in FIELDS}

    if request.method == "POST":
        form = {field: clean(request.form.get(field)) for field in FIELDS}
        if not form["name"]:
            flash("Supplier name is required.", "error")
        else:
            execute(
                """
                INSERT INTO suppliers (name, contact_person, email, phone, address)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    form["name"],
                    form["contact_person"] or None,
                    form["email"] or None,
                    form["phone"] or None,
                    form["address"] or None,
                ),
            )
            flash(f"Supplier \u201c{form['name']}\u201d added.", "success")
            return redirect(url_for("suppliers.index"))

    return render_template(
        "suppliers/form.html",
        page_title="Add supplier",
        active_page="suppliers",
        mode="create",
        form=form,
    )


@suppliers_bp.route("/<int:supplier_id>/edit", methods=["GET", "POST"])
def edit(supplier_id):
    supplier = query("SELECT * FROM suppliers WHERE id = ?", (supplier_id,), one=True)
    if supplier is None:
        abort(404)

    form = {field: supplier[field] or "" for field in FIELDS}

    if request.method == "POST":
        form = {field: clean(request.form.get(field)) for field in FIELDS}
        if not form["name"]:
            flash("Supplier name is required.", "error")
        else:
            execute(
                """
                UPDATE suppliers
                SET name = ?, contact_person = ?, email = ?, phone = ?, address = ?
                WHERE id = ?
                """,
                (
                    form["name"],
                    form["contact_person"] or None,
                    form["email"] or None,
                    form["phone"] or None,
                    form["address"] or None,
                    supplier_id,
                ),
            )
            flash("Supplier updated.", "success")
            return redirect(url_for("suppliers.index"))

    return render_template(
        "suppliers/form.html",
        page_title="Edit supplier",
        active_page="suppliers",
        mode="edit",
        supplier=supplier,
        form=form,
    )


@suppliers_bp.route("/<int:supplier_id>/delete", methods=["POST"])
def delete(supplier_id):
    supplier = query("SELECT name FROM suppliers WHERE id = ?", (supplier_id,), one=True)
    if supplier is None:
        abort(404)

    execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    flash(
        f"Supplier \u201c{supplier['name']}\u201d deleted. Linked products and orders are unchanged.",
        "success",
    )
    return redirect(url_for("suppliers.index"))
