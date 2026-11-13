"""
SQLite helpers.

The connection is created once per request and stored on Flask's `g`
object, then closed automatically when the request finishes. This is the
pattern recommended by the Flask documentation and keeps every query
inside a single, consistent transaction boundary.
"""

import sqlite3

from flask import current_app, g


def get_db():
    """Return the SQLite connection for the current request."""
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        # Return rows as dictionaries so templates can do row["name"].
        connection.row_factory = sqlite3.Row
        # SQLite does not enforce foreign keys unless asked to.
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(error=None):
    """Close the connection at the end of the request."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    """Create every table/index declared in schema.sql (safe to re-run)."""
    db = get_db()
    with current_app.open_resource("database/schema.sql") as schema_file:
        db.executescript(schema_file.read().decode("utf-8"))
    db.commit()


def query(sql, params=(), one=False):
    """
    Run a SELECT and return a list of sqlite3.Row objects.
    Pass one=True to get a single row (or None).
    """
    cursor = get_db().execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    if one:
        return rows[0] if rows else None
    return rows


def scalar(sql, params=(), default=0):
    """Run a query that returns a single value."""
    row = query(sql, params, one=True)
    if row is None or row[0] is None:
        return default
    return row[0]


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE and commit immediately."""
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    last_id = cursor.lastrowid
    cursor.close()
    return last_id


def init_app(app):
    """Hook the database teardown into the Flask app."""
    app.teardown_appcontext(close_db)
