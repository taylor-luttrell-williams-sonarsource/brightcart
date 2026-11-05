import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db


class BrightCartTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app(self.path)
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.path)

    def login(self, email, password="correct-horse-1"):
        self.client.post("/api/auth/register", json={"email": email, "password": password})
        token = self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        ).get_json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_search_returns_matching_products(self):
        res = self.client.get("/api/products/search?q=socks")
        self.assertEqual([p["name"] for p in res.get_json()], ["Merino hiking socks"])

    def test_order_pay_and_list(self):
        h = self.login("carol@example.com")
        order = self.client.post(
            "/api/orders", json={"items": [{"product_id": 2, "quantity": 2}]}, headers=h
        ).get_json()
        self.assertEqual(order["total_cents"], 4800)
        self.assertEqual(self.client.post(f"/api/orders/{order['id']}/pay", headers=h).status_code, 200)
        self.assertEqual(self.client.get("/api/orders", headers=h).get_json()[0]["status"], "paid")

    def test_catalog_import_requires_admin(self):
        h = self.login("dave@example.com")
        res = self.client.post("/api/admin/catalog/import", data="- {name: x, price_cents: 1}", headers=h)
        self.assertEqual(res.status_code, 403)

    def test_admin_can_import_catalog(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'admin')",
                ("root@example.com", generate_password_hash("correct-horse-1")),
            )
            db.commit()
        token = self.client.post(
            "/api/auth/login", json={"email": "root@example.com", "password": "correct-horse-1"}
        ).get_json()["token"]
        res = self.client.post(
            "/api/admin/catalog/import",
            data="- {name: Tent, price_cents: 25000, stock: 5}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.get_json(), {"imported": 1})


if __name__ == "__main__":
    unittest.main()
