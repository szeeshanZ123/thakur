/**
 * Payouts & Dividend Distribution Logic for Captain's Treasure Ledger.
 * Provides transparent uncommitted previews, deterministic remainder breakdowns,
 * and immutable dividend finalization.
 */

let allPayouts = [];
let allVoyages = [];
let allCrew = [];

async function loadPayouts() {
  const container = document.getElementById("payout-table-body");
  showLoading(container, "Loading finalized crew dividends...");

  try {
    const [payoutsList, voyagesList, crewList] = await Promise.all([
      API.getPayouts(),
      API.getVoyages(),
      API.getCrew()
    ]);

    allPayouts = payoutsList || [];
    allVoyages = voyagesList || [];
    allCrew = crewList || [];

    renderPayoutKPIs(allPayouts);
    renderPayoutTable(allPayouts);
    populateVoyageFilters();

    // Check URL parameters for direct preview or finalize trigger
    const urlParams = new URLSearchParams(window.location.search);
    const voyageId = urlParams.get("voyage_id");
    const action = urlParams.get("action");
    if (voyageId) {
      document.getElementById("filter-payout-voyage").value = voyageId;
      filterPayouts();
      if (action === "preview") {
        openPreviewModal(parseInt(voyageId, 10));
      } else if (action === "finalize") {
        openFinalizeModal(parseInt(voyageId, 10));
      }
    }
  } catch (err) {
    console.error("Failed to load payouts:", err);
    showError(container, "Could not load payouts from backend.", loadPayouts);
  }
}

function renderPayoutKPIs(payouts) {
  const container = document.getElementById("payout-kpis");
  if (!container) return;

  const totalDistributed = payouts.reduce((s, p) => s + (p.payout_paise || 0), 0);
  const paidCount = payouts.filter(p => p.status === "finalized" || p.status === "paid").length;
  const uniqueVoyages = new Set(payouts.map(p => p.voyage_id)).size;

  container.innerHTML = `
    <div class="metric-card metric--gold"><div class="metric-label">Total Dividends Distributed</div><div class="metric-value">${formatPaise(totalDistributed)}</div></div>
    <div class="metric-card metric--positive"><div class="metric-label">Finalized Share Records</div><div class="metric-value">${paidCount}</div></div>
    <div class="metric-card"><div class="metric-label">Voyages Distributed</div><div class="metric-value">${uniqueVoyages}</div></div>`;
}

function renderPayoutTable(payouts) {
  const tbody = document.getElementById("payout-table-body");
  if (!tbody) return;

  if (!payouts.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-row">No dividend payouts finalized yet. Select a completed voyage to preview and finalize dividends.</td></tr>';
    return;
  }

  tbody.innerHTML = payouts.map(p => {
    const crew = allCrew.find(c => c.id === p.crew_member_id);
    const crewName = p.crew_member_name || (p.crew_member ? p.crew_member.name : (crew ? crew.name : `Crew #${p.crew_member_id}`));
    const voyage = allVoyages.find(v => v.id === p.voyage_id);
    const voyageName = p.voyage_name || (p.voyage ? p.voyage.name : (voyage ? voyage.name : `Voyage #${p.voyage_id}`));

    return `<tr>
      <td class="td-name"><strong>${crewName}</strong></td>
      <td><span class="badge badge-gold">${shareWeightToDisplay(p.share_weight_units_used)}</span> (<code>${p.share_weight_units_used} units</code>)</td>
      <td>${voyageName}</td>
      <td class="td-amount td-amount-green"><strong>${formatPaise(p.payout_paise)}</strong></td>
      <td>${getStatusBadge(p.status)}</td>
      <td>${formatDate(p.finalized_at || p.calculated_at)}</td>
      <td class="td-actions">
        <button class="btn btn-secondary btn-sm" onclick="openPreviewModal(${p.voyage_id})">View Voyage Shares</button>
      </td>
    </tr>`;
  }).join("");
}

function populateVoyageFilters() {
  const sel = document.getElementById("filter-payout-voyage");
  if (sel) {
    sel.innerHTML = '<option value="">All Voyages</option>' + allVoyages.map(v => `<option value="${v.id}">${v.name} (${v.status})</option>`).join("");
  }
}

function filterPayouts() {
  const search = (document.getElementById("payout-search").value || "").toLowerCase().trim();
  const voyageId = document.getElementById("filter-payout-voyage").value;

  let filtered = allPayouts.filter(p => {
    const crew = allCrew.find(c => c.id === p.crew_member_id);
    const crewName = (crew ? crew.name : "").toLowerCase();
    if (search && !crewName.includes(search)) return false;
    if (voyageId && p.voyage_id !== parseInt(voyageId, 10)) return false;
    return true;
  });

  renderPayoutTable(filtered);
}

async function openPreviewModal(voyageId) {
  if (!voyageId) {
    // Prompt user to pick a voyage
    const completed = allVoyages.filter(v => v.status === "completed");
    if (!completed.length) {
      showToast("No completed voyages available for payout preview", "warn");
      return;
    }
    voyageId = completed[0].id;
  }

  openModal("payout-preview-modal");
  const body = document.getElementById("payout-preview-body");
  showLoading(body, "Calculating exact backend dividend preview...");

  try {
    const preview = await API.previewVoyagePayouts(voyageId);
    renderPreviewDetails(preview);
  } catch (err) {
    showError(body, `Unable to preview payouts: ${err.message}`);
  }
}

function renderPreviewDetails(preview) {
  const body = document.getElementById("payout-preview-body");
  const items = preview.items || [];
  const distProfit = preview.distributable_profit_paise || 0;
  const totalShares = preview.total_share_units || 0;

  body.innerHTML = `
    <div style="margin-bottom: 20px;">
      <h3 style="font-family: var(--font-display); font-size: 22px; color: var(--text-1);">${preview.voyage_name}</h3>
      <p class="muted">Live Uncommitted Dividend Calculation</p>
    </div>

    <div class="kpi-grid" style="margin-bottom: 20px;">
      <div class="metric-card metric--positive"><div class="metric-label">Revenue</div><div class="metric-value">${formatPaise(preview.revenue_paise)}</div></div>
      <div class="metric-card metric--warn"><div class="metric-label">Expenses</div><div class="metric-value">${formatPaise(preview.total_expenses_paise)}</div></div>
      <div class="metric-card metric--gold"><div class="metric-label">Distributable Profit</div><div class="metric-value">${formatPaise(distProfit)}</div></div>
      <div class="metric-card"><div class="metric-label">Total Share Units</div><div class="metric-value">${totalShares} units (${(totalShares / 100).toFixed(2)}x)</div></div>
    </div>

    <h4 class="section-subtitle" style="margin-bottom: 10px;">Eligible Active Crew Entitlements (${items.length})</h4>
    <div class="table-wrapper" style="margin-bottom: 20px;">
      <table>
        <thead>
          <tr>
            <th>Crew Member</th>
            <th>Rank</th>
            <th>Share Weight</th>
            <th>Proportional Payout</th>
          </tr>
        </thead>
        <tbody>
          ${items.length ? items.map(item => `
            <tr>
              <td class="td-name"><strong>${item.crew_member_name}</strong></td>
              <td>${item.rank_name}</td>
              <td class="td-share"><span class="badge badge-gold">${shareWeightToDisplay(item.share_weight_units)}</span> (<code>${item.share_weight_units} units</code>)</td>
              <td class="td-amount td-amount-green"><strong>${formatPaise(item.payout_paise)}</strong></td>
            </tr>
          `).join("") : '<tr><td colspan="4" class="empty-row">No active crew members found for distribution.</td></tr>'}
        </tbody>
      </table>
    </div>

    <!-- Transparent Financial Explanation Accordion -->
    <details class="calc-explanation" style="background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
      <summary style="cursor: pointer; font-weight: 600; color: var(--gold); outline: none;">
        <span>🔍 How was this payout calculated? (Zero-Loss Guarantee)</span>
      </summary>
      <div style="margin-top: 14px; font-size: 13px; color: var(--text-2); line-height: 1.6;">
        <p>1. <strong>Distributable Profit:</strong> Exact Net Profit (<code>${formatPaise(distProfit)}</code>) derived from total credits minus operating expenses.</p>
        <p>2. <strong>Proportional Division:</strong> Each active crew member receives a base payout calculated using integer division: <code>(Distributable Profit × Share Weight Units) // Total Active Share Units</code>.</p>
        <p>3. <strong>Deterministic Remainder Allocation:</strong> Any fractional paise remainder is deterministically allocated to crew members sorted by highest fractional remainder, with Crew ID as the tie-breaker.</p>
        <p style="color: var(--green); margin-top: 8px;"><strong>✓ Exact Invariant:</strong> Sum of all crew payouts strictly equals Distributable Profit with zero lost paise.</p>
      </div>
    </details>

    <div style="text-align: right;">
      <button class="btn btn-gold" onclick="openFinalizeModal(${preview.voyage_id})">Proceed to Finalize Dividends →</button>
    </div>
  `;
}

function openFinalizeModal(voyageId) {
  closeModal("payout-preview-modal");
  const voyage = allVoyages.find(v => v.id === voyageId);
  if (!voyage) return;

  if (voyage.status !== "completed") {
    showToast(`Voyage '${voyage.name}' is '${voyage.status}'. Dividends can only be finalized for completed voyages.`, "error");
    return;
  }

  document.getElementById("finalize-voyage-id").value = voyageId;
  document.getElementById("finalize-voyage-name").textContent = voyage.name;
  openModal("finalize-confirm-modal");
}

async function confirmFinalizePayouts() {
  const voyageId = parseInt(document.getElementById("finalize-voyage-id").value, 10);
  if (!voyageId) return;

  const btn = document.getElementById("confirm-finalize-btn");
  btn.disabled = true;
  btn.textContent = "Finalizing...";

  try {
    const res = await API.finalizeVoyagePayouts(voyageId);
    showToast("Dividends finalized and committed immutably to the ledger!", "success");
    closeModal("finalize-confirm-modal");
    loadPayouts();
  } catch (err) {
    showToast(`Finalization failed: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Finalize Dividends Now";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadPayouts();

  const previewBtn = document.getElementById("preview-payouts-btn");
  if (previewBtn) previewBtn.addEventListener("click", () => openPreviewModal());

  const searchInput = document.getElementById("payout-search");
  if (searchInput) searchInput.addEventListener("input", filterPayouts);

  const voyageFilter = document.getElementById("filter-payout-voyage");
  if (voyageFilter) voyageFilter.addEventListener("change", filterPayouts);

  const confirmBtn = document.getElementById("confirm-finalize-btn");
  if (confirmBtn) confirmBtn.addEventListener("click", confirmFinalizePayouts);
});