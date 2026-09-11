/**
 * Immutable Transaction Ledger Logic for Captain's Treasure Ledger.
 * Displays append-only audit trail and handles authorized reversals and corrections.
 */

let allTransactions = [];
let allVoyages = [];

async function loadLedger() {
  const container = document.getElementById("ledger-table-body");
  showLoading(container, "Loading immutable transaction ledger...");

  try {
    const [txList, voyagesList] = await Promise.all([
      API.getTransactions(),
      API.getVoyages()
    ]);

    allTransactions = txList || [];
    allVoyages = voyagesList || [];

    renderLedgerKPIs(allTransactions);
    renderLedgerTable(allTransactions);
    populateVoyageFilters();
  } catch (err) {
    console.error("Failed to load ledger:", err);
    showError(container, "Could not load transactions from backend.", loadLedger);
  }
}

function renderLedgerKPIs(transactions) {
  const container = document.getElementById("ledger-kpis");
  if (!container) return;

  const totalCredits = transactions.filter(t => t.transaction_type === "CREDIT").reduce((s, t) => s + t.amount_paise, 0);
  const totalDebits = transactions.filter(t => t.transaction_type === "DEBIT").reduce((s, t) => s + t.amount_paise, 0);
  const reversalsCount = transactions.filter(t => t.transaction_type === "REVERSAL").length;

  container.innerHTML = `
    <div class="metric-card metric--positive"><div class="metric-label">Total Credits (Revenue)</div><div class="metric-value">${formatPaise(totalCredits)}</div></div>
    <div class="metric-card metric--warn"><div class="metric-label">Total Debits (Expenses/Payouts)</div><div class="metric-value">${formatPaise(totalDebits)}</div></div>
    <div class="metric-card"><div class="metric-label">Total Ledger Entries</div><div class="metric-value">${transactions.length}</div></div>
    <div class="metric-card metric--gold"><div class="metric-label">Audit Reversals</div><div class="metric-value">${reversalsCount}</div></div>`;
}

function renderLedgerTable(transactions) {
  const tbody = document.getElementById("ledger-table-body");
  if (!tbody) return;

  if (!transactions.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-row">No transactions recorded in the immutable ledger.</td></tr>';
    return;
  }

  tbody.innerHTML = transactions.map(t => {
    const voyage = allVoyages.find(v => v.id === t.voyage_id);
    const voyageName = voyage ? voyage.name : (t.voyage_id ? `Voyage #${t.voyage_id}` : 'Fleet Treasury');
    const isCredit = t.transaction_type === "CREDIT";

    return `<tr>
      <td class="td-id">#${String(t.id).padStart(4, "0")}</td>
      <td>${formatDateTime(t.timestamp)}</td>
      <td>${getStatusBadge(t.transaction_type)}</td>
      <td class="td-amount ${isCredit ? 'td-amount-green' : 'td-amount-red'}">
        <strong>${isCredit ? '+' : '-'}${formatPaise(t.amount_paise)}</strong>
      </td>
      <td class="td-name">${voyageName}</td>
      <td>${t.description}</td>
      <td class="td-actions">
        ${(t.transaction_type === 'CREDIT' || t.transaction_type === 'DEBIT') ? `
          <button class="btn btn-secondary btn-sm" onclick="openReverseModal(${t.id})" title="Record audit reversal entry">Reverse</button>
        ` : '<span class="muted">—</span>'}
      </td>
    </tr>`;
  }).join("");
}

function populateVoyageFilters() {
  const sel = document.getElementById("filter-ledger-voyage");
  if (sel) {
    sel.innerHTML = '<option value="">All Voyages</option>' + allVoyages.map(v => `<option value="${v.id}">${v.name}</option>`).join("");
  }
}

function filterLedger() {
  const search = (document.getElementById("ledger-search").value || "").toLowerCase().trim();
  const voyageId = document.getElementById("filter-ledger-voyage").value;
  const txType = document.getElementById("filter-ledger-type").value;

  let filtered = allTransactions.filter(t => {
    const desc = (t.description || "").toLowerCase();
    if (search && !desc.includes(search)) return false;
    if (voyageId && t.voyage_id !== parseInt(voyageId, 10)) return false;
    if (txType && t.transaction_type !== txType) return false;
    return true;
  });

  renderLedgerTable(filtered);
}

function openReverseModal(txId) {
  const tx = allTransactions.find(t => t.id === txId);
  if (!tx) return;

  document.getElementById("reverse-tx-id").value = txId;
  document.getElementById("reverse-tx-desc").textContent = `#${tx.id} - ${tx.transaction_type} of ${formatPaise(tx.amount_paise)} ("${tx.description}")`;
  document.getElementById("reverse-reason").value = "";
  openModal("reverse-modal");
}

async function submitReversal(e) {
  e.preventDefault();
  const txId = parseInt(document.getElementById("reverse-tx-id").value, 10);
  const reason = document.getElementById("reverse-reason").value.trim();

  if (!reason) {
    showToast("Audit reason is required for transaction reversal", "error");
    return;
  }

  try {
    await API.reverseTransaction(txId, reason);
    showToast(`Reversal entry recorded immutably for Transaction #${txId}!`, "success");
    closeModal("reverse-modal");
    loadLedger();
  } catch (err) {
    showToast(`Reversal failed: ${err.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadLedger();

  const searchInput = document.getElementById("ledger-search");
  if (searchInput) searchInput.addEventListener("input", filterLedger);

  const voyageFilter = document.getElementById("filter-ledger-voyage");
  if (voyageFilter) voyageFilter.addEventListener("change", filterLedger);

  const typeFilter = document.getElementById("filter-ledger-type");
  if (typeFilter) typeFilter.addEventListener("change", filterLedger);

  const reverseForm = document.getElementById("reverse-form");
  if (reverseForm) reverseForm.addEventListener("submit", submitReversal);
});