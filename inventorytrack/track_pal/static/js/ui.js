/* Shared UI scaffolding: sidebar render, icons, helpers */

const ICONS = {
  dash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>',
  warehouse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 21V8l9-5 9 5v13"/><path d="M3 21h18"/><rect x="7" y="13" width="10" height="8"/><path d="M7 17h10"/></svg>',
  box: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/></svg>',
  stock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="6"/><rect x="13" y="7" width="3" height="10"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 9v4M12 17h.01M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>',
  trend: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 17l6-6 4 4 8-8"/><path d="M21 7v5h-5"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>',
  calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  money: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5a2.5 2 0 0 1 5 0c0 1.5-2.5 1.8-2.5 2.5M9.5 14.5a2.5 2 0 0 0 5 0"/></svg>',
  logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20.6 13.4 12 22l-9-9V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5" fill="currentColor"/></svg>',
  swap: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 10l-4 4 4 4"/><path d="M3 14h14"/><path d="M17 14l4-4-4-4"/><path d="M21 10H7"/></svg>',
  produce: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 20h20M4 20V8l5 3V8l5 3V8l5 3v9"/></svg>',
};

const NAV = [
  { href: "/dashboard/",   key: "dash",      label: "Dashboard" },
  { href: "/warehouses/",  key: "warehouse", label: "Warehouses" },
  { href: "/products-ui/", key: "box",       label: "Products" },
  { href: "/sellable-ui/", key: "tag",       label: "Products for Sale" },
  { href: "/stock-ui/",    key: "stock",     label: "Stock Levels" },
  { href: "/transactions-ui/", key: "swap",  label: "Transactions" },
];

/* Redirect to login if there's no token. Call at the top of every
   protected page's load(). Returns false if it redirected. */
function requireAuth() {
  if (!api.isAuthenticated()) {
    window.location.href = "/";
    return false;
  }
  return true;
}

function renderShell(active, me) {
  const links = NAV.map(n =>
    `<a href="${n.href}" class="${n.key === active ? "active" : ""}">${ICONS[n.key]}<span>${n.label}</span></a>`
  ).join("");

  const displayName = me?.name || me?.username || "User";
  const companyName = me?.company || "Stockpile";

  return `
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">S</div>
      <div>
        <div class="brand-name">Stockpile</div>
        <div class="brand-sub">Inventory Control</div>
      </div>
    </div>
    <div class="nav-label">Operations</div>
    <nav class="nav">${links}</nav>
    <div class="side-foot">
      <div class="side-user">
        <div class="avatar">${displayName.slice(0,1).toUpperCase()}</div>
        <div style="flex:1; min-width:0">
          <div style="font-size:13px;font-weight:600">${displayName}</div>
          <small>${companyName}</small>
        </div>
      </div>
      <button class="logout-btn" onclick="api.logout()">${ICONS.logout}<span>Sign out</span></button>
    </div>
  </aside>`;
}

/* Fetch current user, render the sidebar, return the me object so the
   page can also greet them. Call after requireAuth(). */
async function mountShell(active) {
  let me = null;
  try { me = await api.me(); } catch (_) {}
  document.getElementById("sidebar").innerHTML = renderShell(active, me);
  return me;
}

/* Time-aware greeting: "Good morning, Ahmed" */
function greeting(name) {
  const h = new Date().getHours();
  const part = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  return `${part}, ${name || "there"}`;
}

function badgeFor(type) {
  const map = { raw_material: "b-raw", finished_goods: "b-finished", consumables: "b-consumables", OTHERS: "b-others" };
  return `<span class="badge ${map[type] || "b-others"}">${TYPE_LABELS[type] || type}</span>`;
}

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

// money formatter — returns a styled dash if value is null/undefined
function fmtMoney(v) {
  if (v === null || v === undefined) return '<span class="muted-dash">—</span>';
  return `<span class="money">${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>`;
}

// quantity formatter — trims trailing zeros: 100.00 -> 100, 2.50 -> 2.5
function fmtQty(v) {
  if (v === null || v === undefined) return "0";
  const n = Number(v);
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

// label + chip class for a stock row's alert_status from the API
function alertChip(status) {
  if (status === "critical") return '<span class="badge b-low">Critical</span>';
  if (status === "low")      return '<span class="badge b-warn">Low</span>';
  return '<span class="badge b-ok">Healthy</span>';
}

// label + chip class for expiry_status from the API
function expiryChip(status, days) {
  if (status === "expired")       return '<span class="badge chip-expired">Expired</span>';
  if (status === "expiring_soon") return `<span class="badge chip-soon">Expires in ${days}d</span>`;
  if (status === "ok")            return '<span class="badge b-ok">OK</span>';
  return '<span class="muted-dash">—</span>';
}

// kept for any old callers: compute status from raw numbers
function stockState(qty, min, alert) {
  if (qty <= min) return { cls: "b-low", label: "Critical", color: "var(--red)" };
  if (qty <= alert) return { cls: "b-warn", label: "Low", color: "var(--amber)" };
  return { cls: "b-ok", label: "Healthy", color: "var(--green)" };
}

/* Build the alert/expiry banner strip from stock rows (each row has
   alert_status + expiry_status from the API). Returns HTML string. */
function buildBanners(stockRows) {
  const critical = stockRows.filter(s => s.alert_status === "critical");
  const low      = stockRows.filter(s => s.alert_status === "low");
  const expired  = stockRows.filter(s => s.expiry_status === "expired");
  const soon     = stockRows.filter(s => s.expiry_status === "expiring_soon");

  const parts = [];
  if (critical.length) parts.push(`
    <div class="banner banner-critical">${ICONS.alert}
      <div class="banner-text"><strong>${critical.length} product${critical.length>1?"s":""} at critical stock</strong> — at or below minimum level and need restocking now.</div>
      <span class="banner-count">${critical.length}</span>
    </div>`);
  if (low.length) parts.push(`
    <div class="banner banner-warn">${ICONS.alert}
      <div class="banner-text"><strong>${low.length} product${low.length>1?"s":""} running low</strong> — approaching the alert level.</div>
      <span class="banner-count">${low.length}</span>
    </div>`);
  if (expired.length) parts.push(`
    <div class="banner banner-critical">${ICONS.calendar}
      <div class="banner-text"><strong>${expired.length} product${expired.length>1?"s":""} expired</strong> — past expiry date, remove from stock.</div>
      <span class="banner-count">${expired.length}</span>
    </div>`);
  if (soon.length) parts.push(`
    <div class="banner banner-expiry">${ICONS.calendar}
      <div class="banner-text"><strong>${soon.length} product${soon.length>1?"s":""} expiring within 30 days</strong> — plan to use or move them soon.</div>
      <span class="banner-count">${soon.length}</span>
    </div>`);

  return parts.length ? `<div class="banner-stack">${parts.join("")}</div>` : "";
}

window.UI = { ICONS, renderShell, mountShell, greeting, requireAuth, badgeFor, fmtDate, fmtMoney, fmtQty, alertChip, expiryChip, stockState, buildBanners };