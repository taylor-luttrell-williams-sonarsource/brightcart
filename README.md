# BrightCart API

A small Flask + SQLite backend for an outdoor-gear store: product catalog, orders, store credit, refunds, and an admin area.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

On first start the app creates `instance/brightcart.db` and prints the seeded account passwords once.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | Bearer token auth |
| POST | `/api/auth/reset/request`, `/api/auth/reset/confirm` | Password reset by emailed code |
| GET | `/api/products`, `/api/products/search?q=`, `/api/products/<id>` | Public catalog |
| GET/POST | `/api/orders`, `/api/orders/<id>` | Create and view orders |
| POST | `/api/orders/<id>/pay`, `/api/orders/<id>/refund` | Pay by card or store credit; refund to store credit |
| GET/POST | `/api/admin/...` | Users, credit adjustments, YAML catalog import |

## Test

```bash
python -m unittest
```
