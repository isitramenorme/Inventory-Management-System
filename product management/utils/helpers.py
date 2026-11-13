"""Small input helpers shared by the route modules."""

from datetime import datetime


def clean(value, default=""):
    """Trim a form value and coerce None to an empty string."""
    if value is None:
        return default
    return str(value).strip()


def parse_int(value, default=0):
    """Safely convert a form value to an integer."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    """Safely convert a form value to a float."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def today_iso():
    """Local date as YYYY-MM-DD (matches SQLite's date('now','localtime'))."""
    return datetime.now().strftime("%Y-%m-%d")


def next_po_number(prefix, existing_lookup):
    """
    Build a sequential purchase order number such as PO-2026-0004.

    `existing_lookup` is a callable that returns an existing PO row for a
    given number, or None.
    """
    year = datetime.now().year
    base = f"{prefix}-{year}-"
    sequence = 1
    while True:
        candidate = f"{base}{sequence:04d}"
        if existing_lookup(candidate) is None:
            return candidate
        sequence += 1
