/* =============================================================
   API LAYER — Stockpile Inventory System
   -------------------------------------------------------------
   MOCK MODE is on by default. To connect to your Django REST API:
     1. Set USE_MOCK = false
     2. Set API_BASE to your backend (e.g. "https://api.yoursite.com")
     3. Provide an auth token via api.setToken("<jwt>")
   Every method already maps 1:1 to your DRF ViewSets:
     /api/warehouses/   -> warehouseViewSet
     /api/products/     -> productViewSet
     /api/stocks/       -> warehouseStockViewSet
   ============================================================= */

const USE_MOCK = false;  // Toggle this to switch between mock data and real API calls
const API_BASE = "";  // Set this to your Django backend URL when USE_MOCK is false

const ENDPOINTS = {
  warehouses: "/api/warehouses/",
  products:   "/api/products/",
  stocks:     "/api/warehouse-stock/",
};

/* ---------- Mock dataset (mirrors your serializer field names) ---------- */
const MOCK = {
  company: { id: 1, name: "Marina Foods & Trading Co.", manager: "Layla Hassan" },
  warehouses: [
    { id: 1, company: 1, company_name: "Marina Foods & Trading Co.", name: "Central Dry Store", Location: "Alexandria — Smouha", type: "raw_material",   created_by_username: "layla.h", created_at: "2025-01-12T09:00:00Z" },
    { id: 2, company: 1, company_name: "Marina Foods & Trading Co.", name: "Cold Chain Unit A",  Location: "Alexandria — Borg El Arab", type: "finished_goods", created_by_username: "omar.s", created_at: "2025-02-03T09:00:00Z" },
    { id: 3, company: 1, company_name: "Marina Foods & Trading Co.", name: "Packaging Depot",    Location: "Cairo — 6th October", type: "consumables",   created_by_username: "layla.h", created_at: "2025-03-21T09:00:00Z" },
    { id: 4, company: 1, company_name: "Marina Foods & Trading Co.", name: "Overflow Holding",    Location: "Alexandria — Port", type: "OTHERS",        created_by_username: "omar.s", created_at: "2025-04-18T09:00:00Z" },
  ],
  products: [
    { id: 1,  company: 1, sku: "FLR-001", name: "Premium Wheat Flour", description: "Type 55 baking flour", unit: "kg",  minimum_stock_level: 500, alert_stock_level: 800,  net_weight: 25,  gross_weight: 25.4, volume_cbm: 0.03, created_at: "2025-01-15T09:00:00Z" },
    { id: 2,  company: 1, sku: "OIL-014", name: "Sunflower Oil 5L",     description: "Refined cooking oil",  unit: "litre", minimum_stock_level: 200, alert_stock_level: 350, net_weight: 4.6, gross_weight: 5.1, volume_cbm: 0.006, created_at: "2025-01-20T09:00:00Z" },
    { id: 3,  company: 1, sku: "SUG-007", name: "White Sugar",          description: "Granulated, food grade", unit: "kg", minimum_stock_level: 300, alert_stock_level: 500, net_weight: 50, gross_weight: 50.3, volume_cbm: 0.04, created_at: "2025-02-01T09:00:00Z" },
    { id: 4,  company: 1, sku: "BOX-220", name: "Corrugated Box L",     description: "Shipping carton large", unit: "pcs", minimum_stock_level: 1000, alert_stock_level: 1500, net_weight: 0.4, gross_weight: 0.4, volume_cbm: 0.05, created_at: "2025-02-10T09:00:00Z" },
    { id: 5,  company: 1, sku: "TOM-031", name: "Tomato Paste 4.5kg",   description: "Double concentrated",   unit: "box", minimum_stock_level: 150, alert_stock_level: 250, net_weight: 4.5, gross_weight: 4.8, volume_cbm: 0.009, created_at: "2025-03-05T09:00:00Z" },
    { id: 6,  company: 1, sku: "RIC-090", name: "Egyptian Rice",        description: "Short grain premium",   unit: "kg",  minimum_stock_level: 400, alert_stock_level: 600, net_weight: 25, gross_weight: 25.2, volume_cbm: 0.028, created_at: "2025-03-12T09:00:00Z" },
    { id: 7,  company: 1, sku: "LBL-005", name: "Product Labels Roll",  description: "Adhesive labels",       unit: "pcs", minimum_stock_level: 50,  alert_stock_level: 120, net_weight: 1.2, gross_weight: 1.3, volume_cbm: 0.002, created_at: "2025-04-01T09:00:00Z" },
    { id: 8,  company: 1, sku: "BUT-018", name: "Salted Butter Block",  description: "Frozen dairy",          unit: "kg",  minimum_stock_level: 100, alert_stock_level: 180, net_weight: 10, gross_weight: 10.4, volume_cbm: 0.012, created_at: "2025-04-22T09:00:00Z" },
  ],
  stocks: [
    { id: 1, warehouse: 1, warehouse_name: "Central Dry Store", product: 1, product_name: "Premium Wheat Flour", product_sku: "FLR-001", product_unit: "kg",    quantity: 920,  last_updated: "2025-05-28T14:00:00Z" },
    { id: 2, warehouse: 1, warehouse_name: "Central Dry Store", product: 3, product_name: "White Sugar",         product_sku: "SUG-007", product_unit: "kg",    quantity: 410,  last_updated: "2025-05-27T11:00:00Z" },
    { id: 3, warehouse: 1, warehouse_name: "Central Dry Store", product: 6, product_name: "Egyptian Rice",       product_sku: "RIC-090", product_unit: "kg",    quantity: 350,  last_updated: "2025-05-29T08:00:00Z" },
    { id: 4, warehouse: 2, warehouse_name: "Cold Chain Unit A", product: 8, product_name: "Salted Butter Block", product_sku: "BUT-018", product_unit: "kg",    quantity: 95,   last_updated: "2025-05-29T16:00:00Z" },
    { id: 5, warehouse: 2, warehouse_name: "Cold Chain Unit A", product: 5, product_name: "Tomato Paste 4.5kg",  product_sku: "TOM-031", product_unit: "box",   quantity: 230,  last_updated: "2025-05-26T10:00:00Z" },
    { id: 6, warehouse: 1, warehouse_name: "Central Dry Store", product: 2, product_name: "Sunflower Oil 5L",    product_sku: "OIL-014", product_unit: "litre", quantity: 180,  last_updated: "2025-05-30T09:00:00Z" },
    { id: 7, warehouse: 3, warehouse_name: "Packaging Depot",   product: 4, product_name: "Corrugated Box L",    product_sku: "BOX-220", product_unit: "pcs",   quantity: 2200, last_updated: "2025-05-25T13:00:00Z" },
    { id: 8, warehouse: 3, warehouse_name: "Packaging Depot",   product: 7, product_name: "Product Labels Roll", product_sku: "LBL-005", product_unit: "pcs",   quantity: 40,   last_updated: "2025-05-30T15:00:00Z" },
  ],
};

let _seq = 100;
const _delay = (ms = 280) => new Promise(r => setTimeout(r, ms));
const _clone = o => JSON.parse(JSON.stringify(o));

const api = {
  _token: localStorage.getItem("auth_token") || null,
  setToken(t) { this._token = t; localStorage.setItem("auth_token", t); },

  // ---- Auth (djangorestframework-simplejwt) ----
  isAuthenticated() { return !!localStorage.getItem("auth_token"); },

  async login(username, password) {
    // POST /api/token/ -> { access, refresh }
    const res = await fetch(API_BASE + "/api/token/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      let detail = "";
      try { detail = await res.text(); } catch (_) {}
      throw new Error(`LOGIN ${res.status}: ${detail}`);
    }
    const data = await res.json();
    localStorage.setItem("auth_token", data.access);
    if (data.refresh) localStorage.setItem("refresh_token", data.refresh);
    this._token = data.access;
    return data;
  },

  logout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    this._token = null;
    window.location.href = "/";   // back to login
  },

  async _fetch(path, opts = {}) {
    // Grab Django's CSRF token from the page if present
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    const res = await fetch(API_BASE + path, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        ...(this._token ? { Authorization: `Bearer ${this._token}` } : {}),
        ...(opts.headers || {}),
      },
    });

    // token expired or missing -> bounce to login
    if (res.status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("refresh_token");
      this._token = null;
      if (!window.location.pathname.startsWith("/login")) window.location.href = "/";
      throw new Error("API 401: not authenticated");
    }

    if (!res.ok) {
      // Read the response body so we can see exactly what the server objected to
      let detail = "";
      try { detail = await res.text(); } catch (_) {}
      console.error(`API error ${res.status} on ${opts.method || "GET"} ${path}\n`, detail);
      throw new Error(`API ${res.status}: ${detail}`);
    }

    return res.status === 204 ? null : res.json();
  },

  company()      { return USE_MOCK ? _delay().then(() => _clone(MOCK.company)) : this._fetch("/api/company/"); },
  me()           { return USE_MOCK ? _delay().then(() => ({ name: "Manager", company: MOCK.company.name })) : this._fetch("/api/me/"); },
  warehouses()   { return USE_MOCK ? _delay().then(() => _clone(MOCK.warehouses)) : this._fetch(ENDPOINTS.warehouses); },
  products()     { return USE_MOCK ? _delay().then(() => _clone(MOCK.products)) : this._fetch(ENDPOINTS.products); },
  stocks()       { return USE_MOCK ? _delay().then(() => _clone(MOCK.stocks)) : this._fetch(ENDPOINTS.stocks); },
  stocksByWarehouse(id) {
    if (!USE_MOCK) return this._fetch(`${ENDPOINTS.stocks}?warehouse=${id}`);
    return _delay().then(() => _clone(MOCK.stocks.filter(s => s.warehouse === id)));
  },

  createWarehouse(d) {
    if (!USE_MOCK) return this._fetch(ENDPOINTS.warehouses, { method: "POST", body: JSON.stringify(d) });
    return _delay().then(() => {
      const rec = { id: ++_seq, company: 1, company_name: MOCK.company.name, created_by_username: "you", created_at: new Date().toISOString(), ...d };
      MOCK.warehouses.push(rec); return _clone(rec);
    });
  },
  createProduct(d) {
    if (!USE_MOCK) return this._fetch(ENDPOINTS.products, { method: "POST", body: JSON.stringify(d) });
    return _delay().then(() => {
      const rec = { id: ++_seq, company: 1, created_at: new Date().toISOString(), ...d };
      MOCK.products.push(rec); return _clone(rec);
    });
  },
  updateProduct(id, d) {
    if (!USE_MOCK) return this._fetch(`${ENDPOINTS.products}${id}/`, { method: "PATCH", body: JSON.stringify(d) });
    return _delay().then(() => {
      const p = MOCK.products.find(x => x.id === id);
      if (p) Object.assign(p, d);
      return _clone(p);
    });
  },
  deleteProduct(id) {
    if (!USE_MOCK) return this._fetch(`${ENDPOINTS.products}${id}/`, { method: "DELETE" });
    return _delay().then(() => {
      const i = MOCK.products.findIndex(x => x.id === id);
      if (i >= 0) MOCK.products.splice(i, 1);
      return null;
    });
  },

  // ---- Inventory transactions (stock movements) ----
  transactions()        { return this._fetch("/api/transactions/"); },
  createTransaction(d)  { return this._fetch("/api/transactions/", { method: "POST", body: JSON.stringify(d) }); },

  // ---- Sellable products (finished goods with a recipe) ----
  sellables()           { return this._fetch("/api/sellable-products/"); },
  createSellable(d)     { return this._fetch("/api/sellable-products/", { method: "POST", body: JSON.stringify(d) }); },
  updateSellable(id, d) { return this._fetch(`/api/sellable-products/${id}/`, { method: "PATCH", body: JSON.stringify(d) }); },
  deleteSellable(id)    { return this._fetch(`/api/sellable-products/${id}/`, { method: "DELETE" }); },
  produceSellable(id, d){ return this._fetch(`/api/sellable-products/${id}/produce/`, { method: "POST", body: JSON.stringify(d) }); },
  updateStock(id, qty) {
    if (!USE_MOCK) return this._fetch(`${ENDPOINTS.stocks}${id}/`, { method: "PATCH", body: JSON.stringify({ quantity: qty }) });
    return _delay().then(() => {
      const s = MOCK.stocks.find(x => x.id === id);
      if (s) { s.quantity = qty; s.last_updated = new Date().toISOString(); }
      return _clone(s);
    });
  },
};

const TYPE_LABELS = { raw_material: "Raw Material", finished_goods: "Finished Goods", consumables: "Consumables", OTHERS: "Others" };
window.api = api;
window.TYPE_LABELS = TYPE_LABELS;