# StockFlow — Inventory & Stock Management System

A complete, lightweight inventory system for small and medium-sized businesses.
Built with **Flask + SQLite + vanilla HTML/CSS/JS** — no frontend frameworks, no
external services, no build step. The interface uses a clean black-and-white theme.

---

## 1. Requirements

- Python 3.9 or newer (tested on Python 3.11)
- Flask 3.x (`pip install -r requirements.txt`)

SQLite is part of Python's standard library, so Flask is the only extra package.

## 2. Run the application

```powershell
cd "C:\Users\Akshay\OneDrive\Desktop\product management"
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>, or double-click **`run.bat`** on Windows.

The database is created automatically at `instance/inventory.db` on first start.
Delete that file to reset the application (schema and default settings are
recreated on the next run).

## 3. Modules

| Module | What it does |
|---|---|
| **Dashboard** | Totals for products, stock units, low-stock items and inventory value, plus a 7-day stock chart, category split, low-stock alerts and recent activity. Quick links to common tasks. |
| **Products** | Add, edit and delete products. Search by name/SKU, filter by category or stock level. Tracks SKU, category, supplier, unit, cost price, selling price, reorder level and stock. |
| **Categories** | Create, rename and delete categories. Deleting a category keeps its products (they become uncategorised). |
| **Stock movements** | Record stock in, stock out (sale, damage, return, other) or a stocktake adjustment. Every change updates the product quantity and is logged. |
| **Suppliers** | Add, edit and delete suppliers with contact person, email, phone and address. |
| **Purchase orders** | Create orders with multiple line items, mark them as ordered, receive stock (updates quantities and records purchases) or cancel. |
| **Transactions** | Read-only history of purchases, sales and stock updates with type filters and search. |
| **Reports** | Stock valuation at cost and retail, potential margin, category breakdown, top products by value, 30-day activity, purchase order totals and a low-stock report. Print-friendly. |

### Stock rules

- Stock is changed only through **Record movement** or by **receiving a purchase order**, so the audit trail always matches the product quantity.
- Stock out cannot exceed the quantity on hand.
- An adjustment sets the new counted quantity; the difference is recorded as the movement.
- Stock out with reason **Sale** is logged as a sale; other reasons are logged as stock out.

## 4. Project structure

```
product management/
├── app.py                  # Application factory, blueprints, error handlers
├── config.py               # Paths, branding, currency fallback
├── requirements.txt
├── run.bat                 # Windows launcher
│
├── database/
│   ├── db.py               # Connection handling + query helpers
│   └── schema.sql          # Tables, relationships, indexes, defaults
│
├── routes/
│   ├── dashboard.py        # Overview figures and chart
│   ├── products.py         # Product CRUD
│   ├── categories.py       # Category CRUD
│   ├── stock.py            # Movements and stock updates
│   ├── suppliers.py        # Supplier CRUD
│   ├── purchase_orders.py  # Orders, status changes, receiving
│   ├── transactions.py     # Transaction history
│   └── reports.py          # Inventory reports
│
├── utils/
│   ├── filters.py          # money, number, date and time-ago filters
│   └── helpers.py          # Input parsing and PO numbering
│
├── templates/
│   ├── base.html           # Sidebar + top bar + flash messages
│   ├── dashboard.html
│   ├── products/           # list.html, form.html
│   ├── categories/         # list.html
│   ├── stock/              # list.html, form.html
│   ├── suppliers/          # list.html, form.html
│   ├── purchase_orders/    # list.html, form.html, detail.html
│   ├── transactions/       # list.html
│   ├── reports/            # index.html
│   ├── partials/           # sidebar.html, icons.html
│   └── errors/             # 404.html, 500.html
│
├── static/
│   ├── css/style.css       # Monochrome design system + responsive rules
│   ├── js/main.js          # Sidebar drawer and toast helper
│   └── img/favicon.svg
│
└── instance/
    └── inventory.db        # SQLite database (auto-generated)
```

## 5. Database schema

| Table | Purpose |
|---|---|
| `settings` | Key/value app settings (currency, business name) |
| `categories` | Product categories |
| `suppliers` | Supplier contact details |
| `products` | Products, prices, stock quantity, reorder level |
| `stock_movements` | Every stock in / out / adjustment (audit trail) |
| `purchase_orders` | Purchase order headers and status |
| `purchase_order_items` | Line items belonging to a purchase order |
| `transactions` | Purchase / sale / stock transaction history |

Relationships and constraints are declared in `database/schema.sql`:
products reference categories and suppliers, movements reference products,
order items reference orders and products. Foreign keys are enforced on every
connection and CHECK constraints keep prices and quantities valid.

Inspect the database with Python:

```powershell
python -c "import sqlite3; c=sqlite3.connect('instance/inventory.db'); print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")])"
```

## 6. Design notes

- Black-and-white monochrome palette: near-black sidebar, white cards, grey borders.
- Shared sidebar and sticky top bar on every page.
- Responsive: four-column stats collapse to two then one; tables scroll horizontally
  on small screens; the sidebar becomes an off-canvas drawer below 980 px.
- No web fonts, icon packs or CSS frameworks are loaded.
- Currency comes from the `settings` table (`₹` by default) with `config.py` as fallback.

## 7. Notes

- The app is designed for a single local user; there is no login or user management.
- Forms do not use CSRF tokens because the app is intended to run locally.
- `app.py` starts Flask's development server. For a shared network deployment,
  run it behind a production WSGI server and set a real `SECRET_KEY`.
