import os
import secrets

from flask import Flask, request
from flask_wtf.csrf import CSRFProtect

from . import admin, auth, db, orders, products


class TokenAwareCSRFProtect(CSRFProtect):
    """CSRF protection that validates every request carrying ambient (cookie)
    credentials. Requests authenticated solely via a bearer token cannot be
    forged cross-site, so they don't need a CSRF token."""

    def protect(self):
        if not request.cookies or request.headers.get("Authorization", "").startswith("Bearer "):
            return
        super().protect()


csrf = TokenAwareCSRFProtect()


def create_app(db_path=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE"] = db_path or os.path.join(app.instance_path, "brightcart.db")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    csrf.init_app(app)

    db.init_app(app)
    for module in (auth, products, orders, admin):
        app.register_blueprint(module.bp)
    return app
