from flask import Blueprint, g, jsonify, request

from .auth import login_required
from .db import get_db

bp = Blueprint("orders", __name__, url_prefix="/api")


def _order_with_items(db, order_id):
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        return None
    items = db.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    return {**dict(order), "items": [dict(i) for i in items]}


@bp.get("/orders")
@login_required
def list_orders():
    rows = get_db().execute(
        "SELECT id, status, total_cents FROM orders WHERE user_id = ?", (g.user["id"],)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/orders")
@login_required
def create_order():
    lines = (request.get_json(silent=True) or {}).get("items", [])
    if not lines:
        return jsonify(error="items required"), 400
    db = get_db()
    priced, total = [], 0
    for line in lines:
        qty = line.get("quantity", 0)
        product = db.execute(
            "SELECT id, price_cents FROM products WHERE id = ?", (line.get("product_id"),)
        ).fetchone()
        if product is None or not isinstance(qty, int) or not 1 <= qty <= 10:
            return jsonify(error="invalid line item"), 400
        priced.append((product["id"], qty, product["price_cents"]))
        total += qty * product["price_cents"]
    cur = db.execute(
        "INSERT INTO orders (user_id, total_cents, shipping_address) VALUES (?, ?, ?)",
        (g.user["id"], total, g.user["shipping_address"]),
    )
    db.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?, ?)",
        [(cur.lastrowid, pid, qty, price) for pid, qty, price in priced],
    )
    db.commit()
    return jsonify(id=cur.lastrowid, status="pending", total_cents=total), 201


@bp.get("/orders/<int:order_id>")
@login_required
def get_order(order_id):
    order = _order_with_items(get_db(), order_id)
    if order is None:
        return jsonify(error="not found"), 404
    return jsonify(order)


@bp.post("/orders/<int:order_id>/pay")
@login_required
def pay_order(order_id):
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, g.user["id"])
    ).fetchone()
    if order is None:
        return jsonify(error="not found"), 404
    if order["status"] != "pending":
        return jsonify(error="order is not payable"), 409
    method = (request.get_json(silent=True) or {}).get("method", "card")
    if method == "credit":
        if g.user["store_credit_cents"] < order["total_cents"]:
            return jsonify(error="insufficient store credit"), 402
        db.execute(
            "UPDATE users SET store_credit_cents = store_credit_cents - ? WHERE id = ?",
            (order["total_cents"], g.user["id"]),
        )
    db.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))
    db.commit()
    return jsonify(status="paid")


@bp.post("/orders/<int:order_id>/refund")
@login_required
def refund_order(order_id):
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, g.user["id"])
    ).fetchone()
    if order is None:
        return jsonify(error="not found"), 404
    db.execute(
        "UPDATE users SET store_credit_cents = store_credit_cents + ? WHERE id = ?",
        (order["total_cents"], g.user["id"]),
    )
    db.execute("UPDATE orders SET status = 'refunded' WHERE id = ?", (order_id,))
    db.commit()
    return jsonify(status="refunded", credited_cents=order["total_cents"])
