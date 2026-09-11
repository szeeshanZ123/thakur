/**
 * Voyages Management Logic for Captain's Treasure Ledger.
 * Handles expedition lifecycles, revenue postings, financial reconciliation, and manifest exports.
 */

let allVoyages = [];
let currentDetailVoyageId = null;

async function loadVoyages() {
  const container = document.getElementById("voyage-table-body");
  showLoading(container, "Loading maritime expeditions...");

  try {
    allVoyages = await API.getVoyages();
    renderVoyageKPIs(allVoyages);
    renderVoyageTable(allVoyages);
  } catch (err) {
    console.error("Failed to load voyages:", err);
    showError(container, "Could not load voyages from backend.", loadVoyages);
  }
}

function renderVoyageKPIs(voyages) {
  const container = document.getElementById("voyage-kpis");
  if (!container) return;

  const total = voyages.length;
  const completed = voyages.filter(v => v.status === "completed").length;
  const inProgress = voyages.filter(v => v.status === "in_progress" || v.status === "ongoing").length;
  const totalRev = voyages.reduce((s, v) => s + (v.revenue_paise || 0), 0);

  container.innerHTML = `
    <div class="metric-card"><div class="metric-label">Total Expeditions</div><div class="metric-value">${total}</div></div>
    <div class="metric-card metric--positive"><div class="metric-label">Completed</div><div class="metric-value">${completed}</div></div>
    <div class="metric-card metric--warn"><div class="metric-label">In Progress</div><div class="metric-value">${inProgress}</div></div>
    <div class="metric-card metric--hero"><div class="metric-label">Total Loot Revenue</div><div class="metric-value">${formatPaise(totalRev)}</div></div>`;
}

function renderVoyageTable(voyages) {
  const tbody = document.getElementById("voyage-table-body");
  if (!tbody) return;

  if (!voyages.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No voyages recorded yet. Click "Plan New Voyage" to register one.</td></tr>';
    return;
  }

  tbody.innerHTML = voyages.map(v => `
    <tr>
      <td class="td-name"><strong>${v.name}</strong></td>
      <td>${formatDate(v.date)}</td>
      <td>${getStatusBadge(v.status)}</td>
      <td class="td-amount td-amount-green">${formatPaise(v.revenue_paise)}</td>
      <td>${v.description || '<span class="muted">—</span>'}</td>
      <td class="td-actions">
        <button class="btn btn-secondary btn-sm" onclick="viewVoyageDetail(${v.id})">Details & Audit</button>
        <button class="btn btn-secondary btn-sm" onclick="API.downloadExport(${v.id}, 'json')">JSON</button>
        <button class="btn btn-secondary btn-sm" onclick="API.downloadExport(${v.id}, 'csv')">CSV</button>
      </td>
    </tr>
  `).join("");
}

function filterVoyages() {
  const search = (document.getElementById("voyage-search").value || "").toLowerCase().trim();
  const status = document.getElementById("filter-voyage-status").value;

  let filtered = allVoyages.filter(v => {
    if (search && !v.name.toLowerCase().includes(search)) return false;
    if (status && v.status !== status) return false;
    return true;
  });

  renderVoyageTable(filtered);
}

function openCreateVoyageModal() {
  document.getElementById("voyage-form-title").textContent = "Plan New Voyage";
  document.getElementById("voyage-id").value = "";
  document.getElementById("voyage-name").value = "";
  document.getElementById("voyage-date").value = new Date().toISOString().slice(0, 10);
  document.getElementById("voyage-revenue").value = "0";
  document.getElementById("voyage-status").value = "in_progress";
  document.getElementById("voyage-desc").value = "";
  openModal("voyage-modal");
}

async function saveVoyage(e) {
  e.preventDefault();
  const id = document.getElementById("voyage-id").value;
  const name = document.getElementById("voyage-name").value.trim();
  const dateStr = document.getElementById("voyage-date").value;
  const rawRev = document.getElementById("voyage-revenue").value;
  const status = document.getElementById("voyage-status").value;
  const desc = document.getElementById("voyage-desc").value.trim();

  if (!name) {
    showToast("Voyage name is required", "error");
    return;
  }

  const revenuePaise = parseCurrencyToPaise(rawRev);

  const payload = {
    name: name,
    date: dateStr ? new Date(dateStr).toISOString() : new Date().toISOString(),
    revenue_paise: revenuePaise,
    status: status,
    description: desc
  };

  try {
    if (id) {
      await API.updateVoyage(id, payload);
      showToast(`Voyage '${name}' updated!`, "success");
    } else {
      await API.createVoyage(payload);
      showToast(`Voyage '${name}' created successfully!`, "success");
    }
    closeModal("voyage-modal");
    loadVoyages();
  } catch (err) {
    showToast(`Failed to save voyage: ${err.message}`, "error");
  }
}

async function viewVoyageDetail(voyageId) {
  currentDetailVoyageId = voyageId;
  openModal("voyage-detail-modal");
  const body = document.getElementById("detail-body");
  showLoading(body, "Loading voyage financial summary, expenses, payouts, and immutable transactions...");

  try {
    const [voyage, summary, expenses, payouts, transactions] = await Promise.all([
      API.getVoyageById(voyageId),
      API.getVoyageSummary(voyageId).catch(() => null),
      API.getExpenses({ voyage_id: voyageId }).catch(() => []),
      API.getPayouts({ voyage_id: voyageId }).catch(() => []),
      API.getTransactions({ voyage_id: voyageId }).catch(() => [])
    ]);

    document.getElementById("detail-voyage-name").textContent = voyage.name;

    const netProfit = summary ? summary.net_profit_paise : 0;
    const distProfit = summary ? summary.distributable_profit_paise : 0;
    const totalExp = summary ? summary.expenses_paise : 0;
    const rev = summary ? summary.revenue_paise : voyage.revenue_paise;

    body.innerHTML = `
      <div style="margin-bottom:20px;">
        <p class="detail-desc">${voyage.description || "No description provided."}</p>
        <p class="detail-meta">Expedition Date: ${formatDate(voyage.date)} &middot; Status: ${getStatusBadge(voyage.status)}</p>
      </div>

      <!-- Financial Reconciliation Snapshot -->
      <div class="kpi-grid" style="margin-bottom:24px;">
        <div class="metric-card metric--positive">
          <div class="metric-label">Effective Revenue</div>
          <div class="metric-value">${formatPaise(rev)}</div>
        </div>
        <div class="metric-card metric--warn">
          <div class="metric-label">Operating Expenses</div>
          <div class="metric-value">${formatPaise(totalExp)}</div>
        </div>
        <div class="metric-card ${netProfit >= 0 ? 'metric--positive' : 'metric--warn'}">
          <div class="metric-label">Net Profit</div>
          <div class="metric-value">${formatPaise(netProfit)}</div>
        </div>
        <div class="metric-card metric--gold">
          <div class="metric-label">Distributable Profit</div>
          <div class="metric-value">${formatPaise(distProfit)}</div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="toolbar" style="margin-bottom:20px; justify-content: flex-start; gap: 10px;">
        <button class="btn btn-secondary btn-sm" onclick="openAddExpenseFromVoyage(${voyage.id})">+ Add Expense</button>
        <button class="btn btn-secondary btn-sm" onclick="openPostRevenueFromVoyage(${voyage.id}, ${rev})">+ Post Revenue</button>
        <button class="btn btn-primary btn-sm" onclick="previewDividends(${voyage.id})">Preview Dividends</button>
        <button class="btn btn-gold btn-sm" onclick="finalizeDividends(${voyage.id})" ${payouts.length ? 'disabled title="Dividends already finalized"' : ''}>Finalize Dividends</button>
        <button class="btn btn-secondary btn-sm" onclick="API.downloadExport(${voyage.id}, 'json')">Export JSON</button>
        <button class="btn btn-secondary btn-sm" onclick="API.downloadExport(${voyage.id}, 'csv')">Export CSV</button>
      </div>

      <!-- Itemized Expenses Table -->
      <h4 class="section-subtitle" style="margin-bottom: 10px;">Itemized Operational Expenses (${expenses.length})</h4>
      <div class="table-wrapper" style="margin-bottom: 24px;">
        <table>
          <thead>
            <tr><th>Category</th><th>Amount</th><th>Expense Date</th><th>Description</th></tr>
          </thead>
          <tbody>
            ${expenses.length ? expenses.map(e => `
              <tr>
                <td><span class="badge badge-warn">${e.category}</span></td>
                <td class="td-amount td-amount-red"><strong>${formatPaise(e.amount_paise)}</strong></td>
                <td>${formatDate(e.date)}</td>
                <td>${e.description || '—'}</td>
              </tr>
            `).join("") : '<tr><td colspan="4" class="empty-row">No operational expenses recorded.</td></tr>'}
          </tbody>
        </table>
      </div>

      <!-- Finalized Dividend Payouts Table -->
      <h4 class="section-subtitle" style="margin-bottom: 10px;">Crew Dividend Records (${payouts.length})</h4>
      <div class="table-wrapper" style="margin-bottom: 24px;">
        <table>
          <thead>
            <tr><th>Crew Member</th><th>Snapshot Share Units</th><th>Payout Amount</th><th>Status</th><th>Finalized At</th></tr>
          </thead>
          <tbody>
            ${payouts.length ? payouts.map(p => `
              <tr>
                <td class="td-name"><strong>${p.crew_member ? p.crew_member.name : `Crew #${p.crew_member_id}`}</strong></td>
                <td><code>${p.share_weight_units_used} units</code> (${shareWeightToDisplay(p.share_weight_units_used)})</td>
                <td class="td-amount td-amount-green"><strong>${formatPaise(p.payout_paise)}</strong></td>
                <td>${getStatusBadge(p.status)}</td>
                <td>${formatDate(p.finalized_at || p.calculated_at)}</td>
              </tr>
            `).join("") : '<tr><td colspan="5" class="empty-row">Dividends not finalized yet. Click "Preview Dividends" to review.</td></tr>'}
          </tbody>
        </table>
      </div>

      <!-- Chronological Transaction Log -->
      <h4 class="section-subtitle" style="margin-bottom: 10px;">Immutable Transaction Audit Trail (${transactions.length})</h4>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>Tx ID</th><th>Timestamp</th><th>Type</th><th>Amount</th><th>Description</th><th>Ref</th></tr>
          </thead>
          <tbody>
            ${transactions.length ? transactions.map(t => `
              <tr>
                <td class="td-id">#${String(t.id).padStart(4, "0")}</td>
                <td>${formatDateTime(t.timestamp)}</td>
                <td>${getStatusBadge(t.transaction_type)}</td>
                <td class="td-amount ${t.transaction_type === 'CREDIT' ? 'td-amount-green' : 'td-amount-red'}">
                  ${t.transaction_type === 'CREDIT' ? '+' : '-'}${formatPaise(t.amount_paise)}
                </td>
                <td>${t.description}</td>
                <td><code>${t.reference_type || 'manual'}</code></td>
              </tr>
            `).join("") : '<tr><td colspan="6" class="empty-row">No transactions recorded.</td></tr>'}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    showError(body, `Failed to load voyage details: ${err.message}`);
  }
}

function openAddExpenseFromVoyage(voyageId) {
  closeModal("voyage-detail-modal");
  window.location.href = `expenses.html?voyage_id=${voyageId}`;
}

function openPostRevenueFromVoyage(voyageId, currentPaise) {
  const input = prompt(`Enter gross loot revenue in Rupees (e.g. 100000 for ₹100,000):`, (currentPaise / 100).toString());
  if (input === null) return;
  const paise = parseCurrencyToPaise(input);
  if (paise <= 0) {
    showToast("Revenue amount must be greater than zero", "error");
    return;
  }
  API.postVoyageRevenue(voyageId, paise, "Loot revenue posted via voyage command")
    .then(() => {
      showToast("Revenue posted to immutable ledger!", "success");
      viewVoyageDetail(voyageId);
      loadVoyages();
    })
    .catch(err => showToast(`Failed to post revenue: ${err.message}`, "error"));
}

function previewDividends(voyageId) {
  window.location.href = `payouts.html?voyage_id=${voyageId}&action=preview`;
}

function finalizeDividends(voyageId) {
  window.location.href = `payouts.html?voyage_id=${voyageId}&action=finalize`;
}

document.addEventListener("DOMContentLoaded", () => {
  loadVoyages();

  const addBtn = document.getElementById("add-voyage-btn");
  if (addBtn) addBtn.addEventListener("click", openCreateVoyageModal);

  const form = document.getElementById("voyage-form");
  if (form) form.addEventListener("submit", saveVoyage);

  const searchInput = document.getElementById("voyage-search");
  if (searchInput) searchInput.addEventListener("input", filterVoyages);

  const statusFilter = document.getElementById("filter-voyage-status");
  if (statusFilter) statusFilter.addEventListener("change", filterVoyages);
});