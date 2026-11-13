-- =====================================================================
--  StockFlow - SQLite schema
--  Full relational foundation for the inventory system.
--  Tables are created with IF NOT EXISTS, so this file can be run on
--  every application start without losing data.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
--  Application settings (key/value pairs, e.g. currency symbol)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);

-- ---------------------------------------------------------------------
--  Product categories
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
--  Suppliers
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS suppliers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    contact_person TEXT,
    email          TEXT,
    phone          TEXT,
    address        TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
--  Products
--  `quantity` is the current stock on hand. Every change to it should
--  also be recorded in `stock_movements` for a full audit trail.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sku           TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    description   TEXT,
    category_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    supplier_id   INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    unit          TEXT NOT NULL DEFAULT 'pcs',
    cost_price    REAL NOT NULL DEFAULT 0 CHECK (cost_price >= 0),
    selling_price REAL NOT NULL DEFAULT 0 CHECK (selling_price >= 0),
    quantity      INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
--  Stock movements (goods in / goods out / manual adjustments)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_movements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    movement_type TEXT NOT NULL CHECK (movement_type IN ('in', 'out', 'adjustment')),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    reference     TEXT,
    note          TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
--  Purchase orders
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number     TEXT NOT NULL UNIQUE,
    supplier_id   INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    status        TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'ordered', 'received', 'cancelled')),
    order_date    TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    expected_date TEXT,
    total_amount  REAL NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id        INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity          INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost         REAL NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
    line_total        REAL NOT NULL DEFAULT 0 CHECK (line_total >= 0)
);

-- ---------------------------------------------------------------------
--  Transaction history (purchases, sales, stock updates)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    reference    TEXT,
    type         TEXT NOT NULL
                 CHECK (type IN ('purchase', 'sale', 'stock_in', 'stock_out', 'adjustment')),
    product_id   INTEGER REFERENCES products(id) ON DELETE SET NULL,
    quantity     INTEGER NOT NULL DEFAULT 0,
    unit_price   REAL NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    total_amount REAL NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    note         TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
--  Indexes for the lookups the dashboard and modules will perform
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_products_category   ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier   ON products(supplier_id);
CREATE INDEX IF NOT EXISTS idx_products_active     ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_movements_product   ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_created   ON stock_movements(created_at);
CREATE INDEX IF NOT EXISTS idx_po_supplier         ON purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_po_items_order      ON purchase_order_items(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_product ON transactions(product_id);

-- ---------------------------------------------------------------------
--  Default settings (INSERT OR IGNORE keeps existing values intact)
-- ---------------------------------------------------------------------
INSERT OR IGNORE INTO settings (key, value) VALUES ('currency_symbol', '₹');
INSERT OR IGNORE INTO settings (key, value) VALUES ('business_name', 'StockFlow');
INSERT OR IGNORE INTO settings (key, value) VALUES ('low_stock_threshold', '5');
