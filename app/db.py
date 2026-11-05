import secrets
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer',
    store_credit_cents INTEGER NOT NULL DEFAULT 0,
    shipping_address TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending',
    total_cents INTEGER NOT NULL,
    shipping_address TEXT
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reset_codes (
    email TEXT PRIMARY KEY,
    code TEXT NOT NULL
);
"""

SEED_PRODUCTS = [
    ("Trail running shoes", 8900, 40),
    ("Insulated water bottle", 2400, 120),
    ("Merino hiking socks", 1800, 200),
    ("Headlamp 400 lumens", 3500, 60),
    ("Packable rain jacket", 11000, 25),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        _seed(conn)
    conn.commit()


def _seed(conn):
    """Create demo accounts with random passwords and print them once."""
    conn.executemany(
        "INSERT INTO products (name, price_cents, stock) VALUES (?, ?, ?)", SEED_PRODUCTS
    )
    accounts = [
        ("admin@brightcart.example", "admin", 0, "1 Market St, Portland, OR"),
        ("alice@example.com", "customer", 5000, "42 Birch Ave, Denver, CO"),
        ("bob@example.com", "customer", 0, "7 Harbor Rd, Seattle, WA"),
    ]
    for email, role, credit, address in accounts:
        password = secrets.token_urlsafe(12)
        conn.execute(
            "INSERT INTO users (email, password_hash, role, store_credit_cents, shipping_address)"
            " VALUES (?, ?, ?, ?, ?)",
            (email, generate_password_hash(password), role, credit, address),
        )
        print(f"[seed] {email} ({role}) password: {password}")

    # Alice and Bob each have a paid order so the order endpoints have data.
    for user_id, product_id, qty in ((2, 1, 1), (3, 5, 1)):
        price = SEED_PRODUCTS[product_id - 1][1]
        cur = conn.execute(
            "INSERT INTO orders (user_id, status, total_cents, shipping_address)"
            " SELECT ?, 'paid', ?, shipping_address FROM users WHERE id = ?",
            (user_id, price * qty, user_id),
        )
        conn.execute(
            "INSERT INTO order_items VALUES (?, ?, ?, ?)", (cur.lastrowid, product_id, qty, price)
        )
