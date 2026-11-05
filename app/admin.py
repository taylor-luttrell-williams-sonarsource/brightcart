import yaml
from flask import Blueprint, jsonify, request

from .auth import admin_required, login_required
from .db import get_db

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/users")
@admin_required
def list_users():
    rows = get_db().execute(
        "SELECT id, email, role, store_credit_cents FROM users"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/users/<int:user_id>/credit")
@login_required
def adjust_credit(user_id):
    amount = (request.get_json(silent=True) or {}).get("amount_cents")
    if not isinstance(amount, int):
        return jsonify(error="amount_cents must be an integer"), 400
    db = get_db()
    cur = db.execute(
        "UPDATE users SET store_credit_cents = store_credit_cents + ? WHERE id = ?",
        (amount, user_id),
    )
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="not found"), 404
    return jsonify(status="adjusted")


@bp.post("/catalog/import")
@admin_required
def import_catalog():
    """Bulk-load products from a YAML document: a list of name/price_cents/stock entries."""
    entries = yaml.load(request.get_data(as_text=True), Loader=yaml.FullLoader)
    if not isinstance(entries, list):
        return jsonify(error="expected a YAML list"), 400
    db = get_db()
    for e in entries:
        db.execute(
            "INSERT INTO products (name, price_cents, stock) VALUES (?, ?, ?)",
            (e["name"], e["price_cents"], e.get("stock", 0)),
        )
    db.commit()
    return jsonify(imported=len(entries)), 201
