/* ============================================================
   common.js — Shared UI & Financial Presentation System
   ============================================================ */

/* ---------- Icon library (inline SVG, stroke-based) ---------- */
const IC = {
  dashboard: '<path d="M4 20V10M10 20V4M16 20v-6M22 20H2"/>',
  crew: '<circle cx="9" cy="8" r="3.4"/><path d="M2.7 20c.9-3.4 3.4-5.3 6.3-5.3s5.4 1.9 6.3 5.3"/><circle cx="17.2" cy="9.2" r="2.5"/><path d="M16.5 14.8c2.2.3 4 1.6 4.8 3.9"/>',
  ranks: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  voyage: '<path d="M3 15l9 4 9-4"/><path d="M5 15V8h14v7"/><path d="M9 8V5h6v3"/><path d="M3 19v1h18v-1"/>',
  expense: '<circle cx="12" cy="12" r="9"/><path d="M12 7v10"/><path d="M15 9.3C15 8 13.7 7 12 7S9 8 9 9.3s1 1.8 3 1.8 3 .8 3 2.1-1.3 2.1-3 2.1-3-.9-3-2.2"/>',
  payout: '<rect x="2.5" y="6.5" width="19" height="11" rx="2.2"/><circle cx="12" cy="12" r="2.4"/><path d="M6 10v.01M18 14v.01"/>',
  ledger: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v18H6.5A2.5 2.5 0 0 1 4 18.5v-13z"/><path d="M4 18.5A2.5 2.5 0 0 0 6.5 21H20"/>',
  analytics: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  compass: '<circle cx="12" cy="12" r="9.5"/><path d="M15.5 8.5l-2 5-5 2 2-5 5-2z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.5-4.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chevronDown: '<path d="M6 9l6 6 6-6"/>',
  chevronRight: '<path d="M9 6l6 6-6 6"/>',
  chevronUp: '<path d="M6 15l6-6 6 6"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="2.8"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  alert: '<path d="M12 3l9 16H3l9-16z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.5" fill="currentColor"/>',
  flag: '<path d="M5 21V4"/><path d="M5 4c4-2.5 7 2 12 0v8c-5 2-8-2.5-12 0"/>',
  treasure: '<circle cx="12" cy="12" r="8.5"/><circle cx="9" cy="9.5" r="1" fill="currentColor"/><circle cx="15" cy="9.5" r="1" fill="currentColor"/><path d="M8.5 14c.8 1.8 2 2.6 3.5 2.6s2.7-.8 3.5-2.6"/>',
  trendUp: '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
  trendDown: '<path d="M3 7l6 6 4-4 8 8"/><path d="M14 17h7v-7"/>',
  coin: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5c-2 0-3 1-3 2.2s1 2 3 2 3 .7 3 2-1.3 2.3-3 2.3-3-1-3-2.2"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  download: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/>',
  ship: '<path d="M3 15l9 4 9-4"/><path d="M5 15V8h14v7"/><path d="M9 8V5h6v3"/><path d="M3 19v1h18v-1"/>',
  document: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/><path d="M14 3v5h5"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/>'
};

function icon(name, size) {
  const s = size || 0;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${s || '1em'}" height="${s || '1em'}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[name] || ''}</svg>`;
}

function navIcon(name) {
  return icon(name, 19);
}

/* ---------- Financial Formatting & String-to-Paise Parsing ---------- */

/**
 * Converts integer paise into standard Indian Rupee string formatting.
 * ₹150.75 = 15075 paise
 */
function formatPaise(paise, showPence = true) {
  if (paise === null || paise === undefined || isNaN(paise)) return "₹0.00";
  const sign = paise < 0 ? "-" : "";
  const absPaise = Math.abs(paise);
  const rupees = Math.floor(absPaise / 100);
  const remainder = absPaise % 100;
  const rupeeFormatted = rupees.toLocaleString("en-IN");
  if (!showPence && remainder === 0) {
    return `${sign}₹${rupeeFormatted}`;
  }
  return `${sign}₹${rupeeFormatted}.${String(remainder).padStart(2, "0")}`;
}

function formatCurrencyFull(paise) {
  return formatPaise(paise, true);
}

function formatCurrencyFromPaise(paise) {
  if (paise === null || paise === undefined || isNaN(paise)) return "₹0";
  const rupees = Math.abs(paise) / 100;
  const sign = paise < 0 ? "-" : "";
  if (rupees >= 10000000) return `${sign}₹${(rupees / 10000000).toFixed(2)}Cr`;
  if (rupees >= 100000) return `${sign}₹${(rupees / 100000).toFixed(2)}L`;
  if (rupees >= 1000) return `${sign}₹${(rupees / 1000).toFixed(1)}K`;
  return `${sign}₹${Math.floor(rupees).toLocaleString("en-IN")}`;
}

function formatRupeesCompact(rupees) {
  return formatCurrencyFromPaise(rupees * 100);
}

/**
 * Exact string-based decimal parser: parses "150.75" -> 15075 integer paise.
 * Completely immune to JavaScript floating point multiplication quirks.
 */
function parseCurrencyToPaise(inputVal) {
  if (typeof inputVal === "number") {
    inputVal = inputVal.toString();
  }
  if (!inputVal || typeof inputVal !== "string") return 0;
  
  // Clean currency symbols, commas, and whitespace
  let clean = inputVal.replace(/[₹$,\s]/g, "").trim();
  if (!clean) return 0;

  const isNegative = clean.startsWith("-");
  if (isNegative) clean = clean.slice(1).trim();

  const parts = clean.split(".");
  const rupeePart = parseInt(parts[0] || "0", 10) || 0;
  let paisePart = 0;

  if (parts.length > 1) {
    const rawPaiseStr = (parts[1] || "").padEnd(2, "0").slice(0, 2);
    paisePart = parseInt(rawPaiseStr, 10) || 0;
  }

  const total = (rupeePart * 100) + paisePart;
  return isNegative ? -total : total;
}

function shareWeightToDisplay(units) {
  if (units === null || units === undefined) return "0.0x";
  return (units / 100).toFixed(2) + "x";
}

function basisPointsToPercent(bps) {
  if (bps === null || bps === undefined) return "0.00%";
  return (bps / 100).toFixed(2) + "%";
}

/* ---------- Date formatting ---------- */
function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function formatDateTime(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatDateShort(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

/* ---------- Status badges ---------- */
function getStatusBadge(status) {
  if (!status) return '<span class="badge badge-default">—</span>';
  const s = String(status).toLowerCase();
  const map = {
    active: "active", inactive: "inactive",
    completed: "completed", ongoing: "ongoing", in_progress: "ongoing", planned: "planned", cancelled: "inactive",
    paid: "paid", finalized: "paid", calculated: "calculated", pending: "pending",
    credit: "credit", debit: "debit", reversal: "warn", correction: "info",
    profitable: "active", loss: "inactive", break_even: "warn"
  };
  const cls = map[s] || "default";
  const label = s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  return `<span class="badge badge-${cls}">${label}</span>`;
}

/* ---------- Toasts ---------- */
function showToast(message, type = "info") {
  const icons = { success: "treasure", error: "alert", info: "flag", warn: "alert" };
  const container = document.querySelector(".toasts") || createToastContainer();
  const toast = document.createElement("div");
  toast.className = "toast toast-" + type;
  toast.setAttribute("role", "status");
  toast.innerHTML = `<span class="t-ic">${icon(icons[type] || "flag")}</span><span class="t-msg">${message}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("visible"));
  setTimeout(() => {
    toast.classList.remove("visible");
    setTimeout(() => toast.remove(), 260);
  }, 3500);
}

function createToastContainer() {
  const c = document.createElement("div");
  c.className = "toasts";
  document.body.appendChild(c);
  return c;
}

/* ---------- Modals ---------- */
function openModal(id) {
  const m = document.getElementById(id);
  if (!m) return;
  m.classList.add("active");
  document.body.classList.add("no-scroll");
  const focusable = m.querySelector('input, select, textarea, button');
  if (focusable) setTimeout(() => focusable.focus(), 150);
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove("active");
  if (!document.querySelector(".modal-backdrop.active")) document.body.classList.remove("no-scroll");
}

function closeAllModals() {
  document.querySelectorAll(".modal-backdrop.active").forEach(m => m.classList.remove("active"));
  document.body.classList.remove("no-scroll");
}

/* ---------- State builders ---------- */
function showEmptyState(container, title, subtitle, actionLabel, actionFn) {
  container.innerHTML = `
    <div class="state">
      <div class="state-visual">${icon('ship')}</div>
      <h3>${title}</h3>
      <p>${subtitle}</p>
      ${actionLabel ? `<button class="btn btn-primary" data-empty-action>${actionLabel}</button>` : ''}
    </div>`;
  const btn = container.querySelector("[data-empty-action]");
  if (btn && actionFn) btn.addEventListener("click", actionFn);
}

function showLoading(container, text = "Loading ledger data...") {
  container.innerHTML = `<div class="state"><div class="spinner"></div><p class="muted">${text}<span class="loading-dots"></span></p></div>`;
}

function showError(container, text, retryFn) {
  container.innerHTML = `
    <div class="state state-err">
      <div class="state-visual">${icon('alert')}</div>
      <h3>Treasury Error</h3>
      <p>${text || "We couldn't retrieve the latest financial records. Please ensure backend is running."}</p>
      ${retryFn ? `<button class="btn btn-secondary" id="state-retry"><i class="ic">${icon('refresh', 15)}</i><span>Try Again</span></button>` : ""}
    </div>`;
  const btn = container.querySelector("#state-retry");
  if (btn && retryFn) btn.addEventListener("click", retryFn);
}

function showSkeletonMetrics(container, count = 4) {
  let html = "";
  for (let i = 0; i < count; i++) {
    html += `<div class="sk-card skeleton"><div class="skeleton sk-line w40"></div><div class="skeleton sk-line w80" style="height:22px;margin-top:18px"></div></div>`;
  }
  container.innerHTML = `<div class="sk-grid">${html}</div>`;
}

/* ---------- Chart theme ---------- */
const CHART_THEME = {
  legendColor: "#B7AA93",
  tickColor: "#7F7463",
  gridColor: "rgba(64,55,43,0.28)",
  green: "#4FA45B",
  red: "#D84A3F",
  gold: "#C79A3B",
  goldLight: "#D8B765",
  info: "#5B91B5",
  warn: "#D6A23C",
  tooltipStyle: {
    backgroundColor: "rgba(23,19,15,0.96)",
    titleColor: "#F1E6D0",
    titleFont: { family: "'Cormorant Garamond', serif", size: 15, weight: 700 },
    bodyColor: "#B7AA93",
    bodyFont: { family: "'Inter', sans-serif", size: 12 },
    borderColor: "rgba(199,154,59,0.4)",
    borderWidth: 1,
    padding: 12,
    cornerRadius: 8,
    displayColors: true
  },
  baseScales: {
    x: { ticks: { color: "#7F7463", font: { size: 11 } }, grid: { color: "rgba(64,55,43,0.18)" } },
    y: { ticks: { color: "#7F7463", font: { size: 11 } }, grid: { color: "rgba(64,55,43,0.28)" } }
  }
};

/* ---------- Sidebar, Global Role Switcher & Modal Handlers ---------- */
function initCommon() {
  const toggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");

  if (sidebar) {
    const backdrop = document.createElement("div");
    backdrop.className = "sidebar-backdrop";
    backdrop.style.display = "none";
    document.body.appendChild(backdrop);

    const open = () => {
      sidebar.classList.add("open");
      backdrop.style.display = "block";
      requestAnimationFrame(() => backdrop.classList.add("visible"));
      document.body.classList.add("no-scroll");
    };
    const close = () => {
      sidebar.classList.remove("open");
      backdrop.classList.remove("visible");
      setTimeout(() => { backdrop.style.display = "none"; }, 260);
      document.body.classList.remove("no-scroll");
    };

    if (toggle) toggle.addEventListener("click", open);
    backdrop.addEventListener("click", close);
  }

  // Global modal listeners
  document.addEventListener("click", (e) => {
    if (e.target.classList && e.target.classList.contains("modal-backdrop")) closeAllModals();
    if (e.target.closest(".modal-close") || e.target.closest("[data-dismiss-modal]")) closeAllModals();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAllModals();
  });

  // Attach Role Switcher in Sidebar
  const captainCard = document.querySelector(".captain-card");
  if (captainCard && !captainCard.hasAttribute("data-role-clickable")) {
    captainCard.setAttribute("data-role-clickable", "true");
    captainCard.style.cursor = "pointer";
    captainCard.title = "Click to switch role (Captain / Admin / Crew)";
    captainCard.addEventListener("click", () => {
      const current = Auth.getCurrentRole();
      const roles = ["captain", "admin", "crew"];
      const nextRole = roles[(roles.indexOf(current) + 1) % roles.length];
      Auth.setRole(nextRole);
      showToast(`Role switched to: ${nextRole.toUpperCase()}`, "info");
      setTimeout(() => { window.location.reload(); }, 400);
    });
  }
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initCommon);
}