import os

from flask import Flask

from . import admin, auth, db, orders, products


def create_app(db_path=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE"] = db_path or os.path.join(app.instance_path, "brightcart.db")

    db.init_app(app)
    for module in (auth, products, orders, admin):
        app.register_blueprint(module.bp)
    return app
