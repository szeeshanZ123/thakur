let allVoyages = [];

async function loadVoyages() {
  allVoyages = await API.getVoyages();
  renderVoyageKPIs(allVoyages);
  renderVoyageTable(allVoyages);
}

function renderVoyageKPIs(voyages) {
  const total = voyages.length;
  const completed = voyages.filter(v => v.status === "completed").length;
  const ongoing = voyages.filter(v => v.status === "ongoing").length;
  const planned = voyages.filter(v => v.status === "planned").length;
  const totalRev = voyages.reduce((s, v) => s + v.revenue_paise, 0);
  document.getElementById("voyage-kpis").innerHTML = `
    <div class="metric-card"><div class="metric-label">Total Voyages</div><div class="metric-value">${total}</div></div>
    <div class="metric-card metric--positive"><div class="metric-label">Completed</div><div class="metric-value">${completed}</div></div>
    <div class="metric-card"><div class="metric-label">Ongoing</div><div class="metric-value">${ongoing}</div></div>
    <div class="metric-card"><div class="metric-label">Planned</div><div class="metric-value">${planned}</div></div>
    <div class="metric-card metric--hero"><div class="metric-label">Total Revenue</div><div class="metric-value">${formatCurrencyFromPaise(totalRev)}</div></div>`;
}

function renderVoyageTable(voyages) {
  const tbody = document.getElementById("voyage-table-body");
  if (!voyages.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-row">No voyages recorded yet.</td></tr>';
    return;
  }
  tbody.innerHTML = voyages.map(v => {
    const exp = MOCK_EXPENSES.filter(e => e.voyage_id === v.id).reduce((s, e) => s + e.amount_paise, 0);
    const profit = v.revenue_paise - exp;
    return `<tr>
      <td class="td-name" data-label="Voyage">${v.name}</td>
      <td data-label="Date">${formatDate(v.date)}</td>
      <td data-label="Status">${getStatusBadge(v.status)}</td>
      <td class="td-amount" data-label="Revenue">${v.revenue_paise ? formatCurrencyFull(v.revenue_paise) : "\u2014"}</td>
      <td class="td-amount td-amount-red" data-label="Expenses">${exp ? formatCurrencyFull(exp) : "\u2014"}</td>
      <td class="td-amount ${profit >= 0 ? 'td-amount-green' : 'td-amount-red'}" data-label="Profit">${v.revenue_paise ? formatCurrencyFull(profit) : "\u2014"}</td>
      <td class="td-actions" data-label="Actions">
        <button class="btn-icon" onclick="viewVoyageDetail(${v.id})" title="View Details">${icon('eye', 16)}</button>
      </td>
    </tr>`;
  }).join("");
}

function filterVoyages() {
  const search = document.getElementById("voyage-search").value.toLowerCase();
  const status = document.getElementById("filter-voyage-status").value;
  let filtered = allVoyages.filter(v => {
    if (search && !v.name.toLowerCase().includes(search)) return false;
    if (status && v.status !== status) return false;
    return true;
  });
  renderVoyageTable(filtered);
}

function viewVoyageDetail(voyageId) {
  const v = allVoyages.find(x => x.id === voyageId);
  if (!v) return;
  const exp = MOCK_EXPENSES.filter(e => e.voyage_id === v.id);
  const totalExp = exp.reduce((s, e) => s + e.amount_paise, 0);
  const profit = v.revenue_paise - totalExp;
  const payouts = MOCK_PAYOUTS.filter(p => p.voyage_id === v.id);

  document.getElementById("detail-voyage-name").textContent = v.name;
  document.getElementById("detail-body").innerHTML = `
    <div style="margin-bottom:20px">
      <p class="detail-desc">${v.description || "No description"}</p>
      <p class="detail-meta">Date: ${formatDate(v.date)} &middot; Status: ${v.status}</p>
    </div>
    <div class="kpi-grid" style="margin-bottom:24px">
      <div class="metric-card metric--positive"><div class="metric-label">Revenue</div><div class="metric-value">${formatCurrencyFull(v.revenue_paise)}</div></div>
      <div class="metric-card metric--warn"><div class="metric-label">Expenses</div><div class="metric-value">${formatCurrencyFull(totalExp)}</div></div>
      <div class="metric-card ${profit >= 0 ? 'metric--positive' : 'metric--warn'}"><div class="metric-label">Net Profit</div><div class="metric-value">${formatCurrencyFull(profit)}</div></div>
    </div>
    <h4 class="section-subtitle">Expenses</h4>
    <div class="table-shell" style="margin-bottom:20px">
      <table>
        <thead><tr><th>Category</th><th>Description</th><th>Amount</th></tr></thead>
        <tbody>
          ${exp.length ? exp.map(e => `<tr>
            <td data-label="Category">${e.category}</td>
            <td data-label="Description">${e.description}</td>
            <td class="td-amount td-amount-red" data-label="Amount">${formatCurrencyFull(e.amount_paise)}</td>
          </tr>`).join("") : '<tr><td colspan="3" class="empty-row">No expenses recorded.</td></tr>'}
        </tbody>
      </table>
    </div>
    <h4 class="section-subtitle">Crew Payout Distribution</h4>
    <div class="table-shell" style="margin-bottom:16px">
      <table>
        <thead><tr><th>Crew Member</th><th>Rank</th><th>Share</th><th>Payout</th><th>Status</th></tr></thead>
        <tbody>
          ${payouts.length ? payouts.map(p => {
            const crew = MOCK_CREW.find(c => c.id === p.crew_id);
            const rank = MOCK_RANKS.find(r => r.id === (crew ? crew.rank_id : 0));
            return `<tr>
              <td class="td-name" data-label="Crew Member">${crew ? crew.name : "Unknown"}</td>
              <td data-label="Rank">${rank ? rank.name : "Unknown"}</td>
              <td class="td-share" data-label="Share">${shareWeightToDisplay(p.share_weight_units)}</td>
              <td class="td-amount td-amount-green" data-label="Payout">${formatCurrencyFull(p.payout_paise)}</td>
              <td data-label="Status">${getStatusBadge(p.status)}</td>
            </tr>`;
          }).join("") : '<tr><td colspan="5" class="empty-row">No payouts calculated yet.</td></tr>'}
        </tbody>
      </table>
    </div>
    <button class="btn btn-primary" onclick="showToast('Dividend calculation is backend-only. Coming soon!','info')">Calculate Dividends</button>`;
  openModal("modal-voyage-detail");
}

document.addEventListener("DOMContentLoaded", () => {
  initCommon();
  loadVoyages();
  document.getElementById("voyage-search").addEventListener("input", filterVoyages);
  document.getElementById("filter-voyage-status").addEventListener("change", filterVoyages);
  document.getElementById("add-voyage-btn").addEventListener("click", () => openModal("modal-add-voyage"));
  document.getElementById("save-voyage-btn").addEventListener("click", () => {
    showToast("Voyage created (mock)", "success");
    closeAllModals();
  });
});