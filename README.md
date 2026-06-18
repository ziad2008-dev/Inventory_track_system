# Stockpile — Multi-Tenant Inventory & POS System

A full-stack inventory management platform for restaurants and nutrition/supplement companies. Stockpile tracks raw materials, recipes, production, sales, and supplier orders — with multi-tenant company isolation, role-based access control, live analytics, and styled Excel exports.

**Live demo:** [inventorytracksystem-production.up.railway.app](https://inventorytracksystem-production.up.railway.app)

> Built solo with Django REST Framework and a vanilla-JS frontend, deployed on Railway with PostgreSQL.

---

## What it does

Stockpile models the full inventory lifecycle of a production business:

**Receive → Store → Produce → Sell** — every stage tracked, every stock movement logged.

- **Warehouses & products** — multiple storage locations, full product catalog with cost pricing, units, expiry dates, and configurable min/alert stock levels.
- **Recipes & live costing** — define a finished product (e.g. a pizza) as a recipe of raw materials. Cost, profit, and margin are computed live from current ingredient prices.
- **Production** — produce a batch of a finished good: ingredients are deducted from stock atomically (blocked if any ingredient is short), and finished units are added.
- **Record a Sale (POS)** — a restaurant-style basket: ring up "2 pizzas, 1 burger," and recipe-linked items automatically deduct their ingredients. Items without a recipe are still recorded (graceful degradation), so the POS works from day one.
- **Orders with status lifecycle** — incoming (supplier) and outgoing (customer) orders move through *pending → in transit → delivered*. Stock changes **only** on delivery; cancelling a delivered order safely reverses it. Includes shipping details (sea/ground/air, vehicle counts, carrier, tracking, ETA) for businesses that import.
- **Transactions** — manual stock in/out/adjustments with full history.
- **Analytics dashboard** — stock value by warehouse, alert and expiry overviews, sales-over-time, top sellers, and stock movements (Chart.js).
- **Excel export** — styled, filterable `.xlsx` exports (ExcelJS) with conditional formatting on low/critical stock — numbers exported as real numbers for downstream analysis.
- **Roles & permissions** — owner / manager / employee, enforced on the backend (not just hidden UI). Employees can view and sell; managers run operations; owners manage the team.

---

## Architecture

```
Django REST Framework API  ──►  PostgreSQL (multi-tenant, company-scoped)
        │
        ├── JWT auth (djangorestframework-simplejwt)
        ├── Atomic stock operations (db transactions, row locking)
        └── Role-based permissions (DRF permission classes)

Vanilla-JS frontend (served as Django templates + static)
        ├── Token auth, per-page role gating
        ├── Chart.js (analytics), ExcelJS (exports)
        └── Dark "control-room" UI, custom design system
```

### Multi-tenancy
Every model is scoped to a `company`. A `UserProfile` links each user to one company and carries their role. All API queries filter by the requesting user's company, so data is isolated at the query layer — users only ever see their own company's records.

### Data integrity
Stock-moving operations (production, sales, order delivery, transactions) run inside atomic database transactions with `select_for_update` row locking. If any part fails — e.g. an ingredient is short mid-basket — the entire operation rolls back, so stock counts can never be left half-updated.

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Django 6, Django REST Framework |
| Auth | JWT (simplejwt) |
| Database | PostgreSQL (dj-database-url) |
| Frontend | Vanilla JavaScript, HTML, CSS (no framework) |
| Charts | Chart.js |
| Excel | ExcelJS (browser-side, styled) |
| Static files | WhiteNoise |
| Server | Gunicorn |
| Hosting | Railway |

---

## Key data models

- **company** — the tenant; holds settings like the default sales warehouse.
- **UserProfile** — links a user to a company + role (owner/manager/employee).
- **warehouse / product / warehouse_stock** — storage, catalog, and per-warehouse quantities (decimal, for fractional stock).
- **SellableProduct / RecipeItem** — finished goods and their ingredient recipes; auto-links a stockable finished product.
- **InventoryTransaction** — every stock movement, with type and audit trail.
- **StockOrder** — incoming/outgoing orders with status lifecycle + shipping logistics.
- **Sale / SaleItem** — recorded sales (POS), with line items and revenue totals.

---

## Running locally

```bash
# clone
git clone https://github.com/YOURNAME/stockpile.git
cd stockpile/inventorytrack

# install
pip install -r requirements.txt

# configure — copy the example and fill in your values
cp .env.example .env        # then edit .env

# database
python manage.py migrate
python manage.py createsuperuser

# run
python manage.py runserver
```

Set `DEBUG=True` locally for development. Configuration (secret key, database, debug) is read from environment variables — see `.env.example`.

> **Note:** After creating a superuser, assign them a `UserProfile` (linking to a company) in the Django admin, or the multi-tenant filter will show empty lists.

---

## Notable engineering decisions

- **Stock changes only at the right moment.** Orders don't touch stock until delivered; production blocks if ingredients are short; sales handle unregistered items gracefully. The data stays truthful to physical reality.
- **Backend-enforced roles.** UI hiding is cosmetic — the real permission checks live in DRF permission classes, so a restricted user is restricted even via direct API calls.
- **Decimal-safe money math.** All quantities and prices are decimals, with careful conversion to avoid floating-point and string-concatenation bugs.
- **Browser-side Excel.** Exports are generated client-side with ExcelJS, so there's no server load and the output respects the user's company filter automatically.

---

## Roadmap ideas

- Email-invite flow for adding team members
- Lot/batch traceability (for nutrition/supplement compliance)
- FEFO (first-expired-first-out) consumption logic
- Cost/margin and waste-tracking reports

---

*Built by [Ziad](https://github.com/YOURNAME) — a data analyst and Django developer.*
