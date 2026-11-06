from flask import Blueprint, jsonify, request

from .db import get_db

bp = Blueprint("products", __name__, url_prefix="/api")


@bp.get("/products")
def list_products():
    rows = get_db().execute("SELECT id, name, price_cents, stock FROM products").fetchall()
    return jsonify([dict(r) for r in rows])


@bp.get("/products/search")
def search_products():
    q = request.args.get("q", "")
    query = "SELECT id, name, price_cents FROM products WHERE name LIKE ?"
    rows = get_db().execute(query, (f"%{q}%",)).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.get("/products/<int:product_id>")
def get_product(product_id):
    row = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        return jsonify(error="not found"), 404
    return jsonify(dict(row))
