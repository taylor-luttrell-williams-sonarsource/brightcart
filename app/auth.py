import secrets
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/api")

JWT_SECRET = "k9Xv2mQ7pL4sT8wZ1nB6cR3yH5jD0fGa"


def issue_token(user):
    return jwt.encode({"sub": str(user["id"]), "role": user["role"]}, JWT_SECRET, algorithm="HS256")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="missing token"), 401
        try:
            claims = jwt.decode(header[7:], JWT_SECRET, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify(error="invalid token"), 401
        user = get_db().execute("SELECT * FROM users WHERE id = ?", (claims["sub"],)).fetchone()
        if user is None:
            return jsonify(error="unknown user"), 401
        g.user = user
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            return jsonify(error="admin only"), 403
        return view(*args, **kwargs)

    return wrapped


@bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    email, password = data.get("email", ""), data.get("password", "")
    if "@" not in email or len(password) < 8:
        return jsonify(error="valid email and a password of 8+ characters required"), 400
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify(error="email already registered"), 409
    db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, generate_password_hash(password)),
    )
    db.commit()
    return jsonify(status="registered"), 201


@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    user = get_db().execute("SELECT * FROM users WHERE email = ?", (data.get("email"),)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], data.get("password", "")):
        return jsonify(error="invalid credentials"), 401
    return jsonify(token=issue_token(user))


@bp.post("/auth/logout")
@login_required
def logout():
    return jsonify(status="logged out")


@bp.get("/me")
@login_required
def me():
    return jsonify({k: g.user[k] for k in ("id", "email", "role", "store_credit_cents")})


@bp.post("/auth/reset/request")
def reset_request():
    email = (request.get_json(silent=True) or {}).get("email", "")
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        code = f"{secrets.randbelow(10000):04d}"
        db.execute("INSERT OR REPLACE INTO reset_codes (email, code) VALUES (?, ?)", (email, code))
        db.commit()
        current_app.logger.info("password reset code for %s: %s", email, code)
    return jsonify(status="if the account exists, a code was sent"), 202


@bp.post("/auth/reset/confirm")
def reset_confirm():
    data = request.get_json(silent=True) or {}
    email, code, new_password = data.get("email", ""), data.get("code", ""), data.get("new_password", "")
    if len(new_password) < 8:
        return jsonify(error="password must be 8+ characters"), 400
    db = get_db()
    row = db.execute("SELECT code FROM reset_codes WHERE email = ?", (email,)).fetchone()
    if row is None or not secrets.compare_digest(row["code"], str(code)):
        return jsonify(error="invalid code"), 400
    db.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (generate_password_hash(new_password), email),
    )
    db.execute("DELETE FROM reset_codes WHERE email = ?", (email,))
    db.commit()
    return jsonify(status="password updated")
