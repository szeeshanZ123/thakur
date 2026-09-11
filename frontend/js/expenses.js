let allExpenses = [];

async function loadExpenses() {
  allExpenses = await API.getExpenses();
  renderExpenseKPIs(allExpenses);
  renderExpenseTable(allExpenses);
  populateExpenseVoyageFilter();
  populateAddExpenseVoyages();
}

function renderExpenseKPIs(expenses) {
  const total = expenses.reduce((s, e) => s + e.amount_paise, 0);
  const shipRepair = expenses.filter(e => e.category === "Ship Repair").reduce((s, e) => s + e.amount_paise, 0);
  const gunpowder = expenses.filter(e => e.category === "Gunpowder").reduce((s, e) => s + e.amount_paise, 0);
  const provisions = expenses.filter(e => e.category === "Provisions").reduce((s, e) => s + e.amount_paise, 0);
  document.getElementById("expense-kpis").innerHTML = `
    <div class="metric-card metric--warn"><div class="metric-label">Total Expenses</div><div class="metric-value">${formatCurrencyFromPaise(total)}</div></div>
    <div class="metric-card"><div class="metric-label">Ship Repairs</div><div class="metric-value">${formatCurrencyFromPaise(shipRepair)}</div></div>
    <div class="metric-card"><div class="metric-label">Gunpowder</div><div class="metric-value">${formatCurrencyFromPaise(gunpowder)}</div></div>
    <div class="metric-card"><div class="metric-label">Provisions</div><div class="metric-value">${formatCurrencyFromPaise(provisions)}</div></div>`;
}

function renderExpenseTable(expenses) {
  const tbody = document.getElementById("expense-table-body");
  if (!expenses.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No expenses recorded.</td></tr>';
    return;
  }
  tbody.innerHTML = expenses.map(e => {
    const v = MOCK_VOYAGES.find(v => v.id === e.voyage_id);
    return `<tr>
      <td data-label="Date">${formatDate(e.date)}</td>
      <td class="td-name" data-label="Voyage">${v ? v.name : "Unknown"}</td>
      <td data-label="Category">${e.category}</td>
      <td data-label="Description">${e.description}</td>
      <td class="td-amount td-amount-red" data-label="Amount">${formatCurrencyFull(e.amount_paise)}</td>
      <td class="td-actions" data-label="Actions"><button class="btn-icon" title="View">${icon('eye', 16)}</button></td>
    </tr>`;
  }).join("");
}

function filterExpenses() {
  const search = document.getElementById("expense-search").value.toLowerCase();
  const category = document.getElementById("filter-expense-category").value;
  const voyageId = document.getElementById("filter-expense-voyage").value;
  let filtered = allExpenses.filter(e => {
    if (search && !e.description.toLowerCase().includes(search) && !e.category.toLowerCase().includes(search)) return false;
    if (category && e.category !== category) return false;
    if (voyageId && e.voyage_id !== parseInt(voyageId)) return false;
    return true;
  });
  renderExpenseTable(filtered);
}

function populateExpenseVoyageFilter() {
  const sel = document.getElementById("filter-expense-voyage");
  sel.innerHTML = '<option value="">All Voyages</option>' + MOCK_VOYAGES.map(v => `<option value="${v.id}">${v.name}</option>`).join("");
}

function populateAddExpenseVoyages() {
  document.getElementById("exp-voyage").innerHTML = MOCK_VOYAGES.map(v => `<option value="${v.id}">${v.name}</option>`).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  initCommon();
  loadExpenses();
  document.getElementById("expense-search").addEventListener("input", filterExpenses);
  document.getElementById("filter-expense-category").addEventListener("change", filterExpenses);
  document.getElementById("filter-expense-voyage").addEventListener("change", filterExpenses);
  document.getElementById("add-expense-btn").addEventListener("click", () => openModal("modal-add-expense"));
  document.getElementById("save-expense-btn").addEventListener("click", () => {
    showToast("Expense added (mock)", "success");
    closeAllModals();
  });
});