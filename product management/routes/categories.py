"""Category management: simple list + inline add/edit form."""

import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from database.db import execute, query
from utils.helpers import clean, parse_int

categories_bp = Blueprint("categories", __name__, url_prefix="/categories")


@categories_bp.route("/")
def index():
    edit_id = parse_int(request.args.get("edit"), 0)
    editing = None
    if edit_id:
        editing = query("SELECT * FROM categories WHERE id = ?", (edit_id,), one=True)

    categories = query(
        """
        SELECT c.*,
               COUNT(p.id) AS product_count,
               COALESCE(SUM(p.quantity), 0) AS units,
               COALESCE(SUM(p.quantity * p.cost_price), 0) AS stock_value
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.is_active = 1
        GROUP BY c.id
        ORDER BY c.name COLLATE NOCASE
        """
    )

    return render_template(
        "categories/list.html",
        page_title="Categories",
        active_page="categories",
        categories=categories,
        editing=editing,
    )


@categories_bp.route("/save", methods=["POST"])
def save():
    category_id = parse_int(request.form.get("id"), 0)
    name = clean(request.form.get("name"))
    description = clean(request.form.get("description"))

    if not name:
        flash("Category name is required.", "error")
        return redirect(url_for("categories.index"))

    try:
        if category_id:
            execute(
                "UPDATE categories SET name = ?, description = ? WHERE id = ?",
                (name, description or None, category_id),
            )
            flash("Category updated.", "success")
        else:
            execute(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (name, description or None),
            )
            flash(f"Category \u201c{name}\u201d added.", "success")
    except sqlite3.IntegrityError:
        flash("A category with that name already exists.", "error")

    return redirect(url_for("categories.index"))


@categories_bp.route("/<int:category_id>/delete", methods=["POST"])
def delete(category_id):
    category = query("SELECT name FROM categories WHERE id = ?", (category_id,), one=True)
    if category is None:
        abort(404)

    execute("DELETE FROM categories WHERE id = ?", (category_id,))
    flash(
        f"Category \u201c{category['name']}\u201d deleted. Its products are now uncategorised.",
        "success",
    )
    return redirect(url_for("categories.index"))
