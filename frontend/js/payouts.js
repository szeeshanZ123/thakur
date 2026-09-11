let allPayouts = [];

async function loadPayouts() {
  allPayouts = await API.getPayouts();
  renderPayoutKPIs(allPayouts);
  renderPayoutTable(allPayouts);
  populatePayoutFilters();
}

function renderPayoutKPIs(payouts) {
  const total = payouts.reduce((s, p) => s + p.payout_paise, 0);
  const paid = payouts.filter(p => p.status === "paid").reduce((s, p) => s + p.payout_paise, 0);
  const calculated = payouts.filter(p => p.status === "calculated").reduce((s, p) => s + p.payout_paise, 0);
  const pending = payouts.filter(p => p.status === "pending").reduce((s, p) => s + p.payout_paise, 0);
  document.getElementById("payout-kpis").innerHTML = `
    <div class="metric-card metric--gold"><div class="metric-label">Total Distributed</div><div class="metric-value">${formatCurrencyFromPaise(total)}</div></div>
    <div class="metric-card metric--positive"><div class="metric-label">Paid</div><div class="metric-value">${formatCurrencyFromPaise(paid)}</div></div>
    <div class="metric-card"><div class="metric-label">Calculated</div><div class="metric-value">${formatCurrencyFromPaise(calculated)}</div></div>
    <div class="metric-card metric--warn"><div class="metric-label">Pending</div><div class="metric-value">${formatCurrencyFromPaise(pending)}</div></div>`;
}

function renderPayoutTable(payouts) {
  const tbody = document.getElementById("payout-table-body");
  if (!payouts.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No payouts recorded.</td></tr>';
    return;
  }
  tbody.innerHTML = payouts.map(p => {
    const crew = MOCK_CREW.find(c => c.id === p.crew_id);
    const rank = MOCK_RANKS.find(r => r.id === (crew ? crew.rank_id : 0));
    const voyage = MOCK_VOYAGES.find(v => v.id === p.voyage_id);
    return `<tr>
      <td class="td-name" data-label="Crew Member">${crew ? crew.name : "Unknown"}</td>
      <td data-label="Rank">${rank ? rank.name : "Unknown"}</td>
      <td data-label="Voyage">${voyage ? voyage.name : "Unknown"}</td>
      <td class="td-share" data-label="Share">${shareWeightToDisplay(p.share_weight_units)}</td>
      <td class="td-amount td-amount-green" data-label="Payout">${formatCurrencyFull(p.payout_paise)}</td>
      <td data-label="Status">${getStatusBadge(p.status)}</td>
      <td data-label="Date">${formatDate(p.date)}</td>
      <td class="td-actions" data-label="Actions">
        <button class="btn-icon" onclick="showPayoutPreview(${p.voyage_id})" title="View Distribution">${icon('eye', 16)}</button>
      </td>
    </tr>`;
  }).join("");
}

function filterPayouts() {
  const search = document.getElementById("payout-search").value.toLowerCase();
  const status = document.getElementById("filter-payout-status").value;
  const voyageId = document.getElementById("filter-payout-voyage").value;
  let filtered = allPayouts.filter(p => {
    const crew = MOCK_CREW.find(c => c.id === p.crew_id);
    if (search && crew && !crew.name.toLowerCase().includes(search)) return false;
    if (status && p.status !== status) return false;
    if (voyageId && p.voyage_id !== parseInt(voyageId)) return false;
    return true;
  });
  renderPayoutTable(filtered);
}

function populatePayoutFilters() {
  document.getElementById("filter-payout-voyage").innerHTML = '<option value="">All Voyages</option>' + MOCK_VOYAGES.map(v => `<option value="${v.id}">${v.name}</option>`).join("");
}

function showPayoutPreview(voyageId) {
  const voyage = MOCK_VOYAGES.find(v => v.id === voyageId);
  if (!voyage) return;
  const expenses = MOCK_EXPENSES.filter(e => e.voyage_id === voyageId);
  const totalExp = expenses.reduce((s, e) => s + e.amount_paise, 0);
  const profit = voyage.revenue_paise - totalExp;
  const payouts = MOCK_PAYOUTS.filter(p => p.voyage_id === voyageId);
  const totalShares = payouts.reduce((s, p) => s + p.share_weight_units, 0);
  const valuePerShare = totalShares ? Math.round(profit / totalShares) : 0;

  document.getElementById("payout-preview-body").innerHTML = `
    <div class="voyage-title">${voyage.name}</div>
    <div class="voyage-subtitle">Dividend Distribution</div>
    <div class="payout-summary-grid">
      <div class="payout-summary-item"><div class="ps-label">Revenue</div><div class="ps-value td-amount-green">${formatCurrencyFull(voyage.revenue_paise)}</div></div>
      <div class="payout-summary-item"><div class="ps-label">Expenses</div><div class="ps-value td-amount-red">${formatCurrencyFull(totalExp)}</div></div>
      <div class="payout-summary-item"><div class="ps-label">Net Profit</div><div class="ps-value">${formatCurrencyFull(profit)}</div></div>
    </div>
    <div style="text-align:center;margin-bottom:16px"><span class="detail-label">Total Shares: </span><span class="td-share">${(totalShares/100).toFixed(1)}</span></div>
    <div class="payout-list">
      ${payouts.map(p => {
        const crew = MOCK_CREW.find(c => c.id === p.crew_id);
        const rank = MOCK_RANKS.find(r => r.id === (crew ? crew.rank_id : 0));
        return `<div class="payout-row">
          <div class="pr-info">
            <div><div class="pr-name">${crew ? crew.name : "Unknown"}</div><div class="pr-rank">${rank ? rank.name : "Unknown"}</div></div>
          </div>
          <div class="pr-share">${shareWeightToDisplay(p.share_weight_units)}</div>
          <div class="pr-amount">${formatCurrencyFull(p.payout_paise)}</div>
        </div>`;
      }).join("")}
    </div>
    <div class="calc-explanation">
      <h4>How was this calculated?</h4>
      <div class="calc-lines">
        Revenue<br>
        &nbsp;&nbsp;\u2212 Expenses<br>
        \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500<br>
        <span class="calc-highlight">Net Profit: ${formatCurrencyFull(profit)}</span><br><br>
        Net Profit<br>
        &nbsp;&nbsp;\u00F7 Total Shares (${(totalShares/100).toFixed(1)})<br>
        \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500<br>
        <span class="calc-highlight">Value Per Share: ${formatCurrencyFull(valuePerShare)}</span><br><br>
        Value Per Share<br>
        &nbsp;&nbsp;\u00D7 Crew Share<br>
        \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500<br>
        <span class="calc-highlight">Crew Payout</span>
      </div>
    </div>`;
  openModal("modal-payout-preview");
}

document.addEventListener("DOMContentLoaded", () => {
  initCommon();
  loadPayouts();
  document.getElementById("payout-search").addEventListener("input", filterPayouts);
  document.getElementById("filter-payout-status").addEventListener("change", filterPayouts);
  document.getElementById("filter-payout-voyage").addEventListener("change", filterPayouts);
});