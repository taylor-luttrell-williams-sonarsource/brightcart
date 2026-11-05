# Seeded issues (for demo use only)

This project intentionally contains real, exploitable issues so SonarQube SAST, SCA, and
Hunter Agent each have something genuine to find. Do not deploy this code or reuse these
patterns.

## SAST — SQL injection (`app/products.py`)

`search_products` builds a query with an f-string instead of a parameter:

```python
query = f"SELECT id, name, price_cents FROM products WHERE name LIKE '%{q}%'"
```

`q` comes straight from `?q=` with no escaping. A UNION-based payload against this
endpoint can read arbitrary columns from any table, including `users.password_hash`.
Compelling because it's a public, unauthenticated endpoint and the payoff is full
credential exposure.

## SCA — vulnerable dependency (`requirements.txt`)

`PyYAML==5.3.1` is pinned. `app/admin.py` calls `yaml.load(..., Loader=yaml.FullLoader)`
on the catalog import endpoint. Versions before 5.4 allow arbitrary Python object
construction through `FullLoader`, tracked as CVE-2020-1747 — a YAML payload can execute
code on the server. SCA should flag the dependency itself; the `yaml.load` call is a
secondary SAST-visible hotspot.

## Hunter Agent — one issue per logic-flaw category

**Broken access control** — `GET /api/orders/<id>` (`app/orders.py`) only checks that the
caller is logged in, not that they own the order, so any authenticated user can read any
other customer's order and shipping address (IDOR). `POST /api/admin/users/<id>/credit`
(`app/admin.py`) is decorated with `@login_required` instead of `@admin_required`, so any
logged-in customer can grant themselves unlimited store credit.

**Business-logic abuse** — `POST /api/orders/<id>/refund` credits the order total to the
caller's store-credit balance and marks the order "refunded," but never checks that the
order was ever paid, and can be called repeatedly on the same order since nothing
prevents a second refund on an already-refunded order. A customer can place an order and
call refund on it any number of times for unlimited free store credit.

**Authentication / session flaws** — `POST /api/auth/reset/confirm` checks a 4-digit
numeric reset code with no rate limit or lockout. All 10,000 codes can be tried in a
normal-speed loop, so any account's password (including the admin account) can be reset
without ever receiving the code.
