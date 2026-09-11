/**
 * Expenses Management Logic for Captain's Treasure Ledger.
 * Records categorized operational debits atomically into the immutable ledger.
 */

let allExpenses = [];
let allVoyages = [];

async function loadExpenses() {
  const container = document.getElementById("expense-table-body");
  showLoading(container, "Loading operational expenses...");

  try {
    const [expensesList, voyagesList] = await Promise.all([
      API.getExpenses(),
      API.getVoyages()
    ]);

    allExpenses = expensesList || [];
    allVoyages = voyagesList || [];

    renderExpenseKPIs(allExpenses);
    renderExpenseTable(allExpenses);
    populateVoyageDropdowns();

    // Check URL query param for preselected voyage
    const urlParams = new URLSearchParams(window.location.search);
    const preselectedVoyage = urlParams.get("voyage_id");
    if (preselectedVoyage) {
      document.getElementById("filter-expense-voyage").value = preselectedVoyage;
      filterExpenses();
      openAddExpenseModal(parseInt(preselectedVoyage, 10));
    }
  } catch (err) {
    console.error("Failed to load expenses:", err);
    showError(container, "Could not load expenses from backend.", loadExpenses);
  }
}

function renderExpenseKPIs(expenses) {
  const container = document.getElementById("expense-kpis");
  if (!container) return;

  const total = expenses.reduce((s, e) => s + (e.amount_paise || 0), 0);
  const categoriesCount = new Set(expenses.map(e => e.category)).size;

  container.innerHTML = `
    <div class="metric-card metric--warn"><div class="metric-label">Total Operating Expenses</div><div class="metric-value">${formatPaise(total)}</div></div>
    <div class="metric-card"><div class="metric-label">Logged Expense Items</div><div class="metric-value">${expenses.length}</div></div>
    <div class="metric-card"><div class="metric-label">Active Categories</div><div class="metric-value">${categoriesCount}</div></div>`;
}

function renderExpenseTable(expenses) {
  const tbody = document.getElementById("expense-table-body");
  if (!tbody) return;

  if (!expenses.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No expenses found matching filters.</td></tr>';
    return;
  }

  tbody.innerHTML = expenses.map(e => {
    const voyage = allVoyages.find(v => v.id === e.voyage_id);
    const voyageName = e.voyage_name || (voyage ? voyage.name : `Voyage #${e.voyage_id}`);

    return `<tr>
      <td class="td-id">#${String(e.id).padStart(3, "0")}</td>
      <td class="td-name"><strong>${voyageName}</strong></td>
      <td><span class="badge badge-warn">${e.category}</span></td>
      <td class="td-amount td-amount-red"><strong>${formatPaise(e.amount_paise)}</strong></td>
      <td>${formatDate(e.date)}</td>
      <td>${e.description || '<span class="muted">—</span>'}</td>
    </tr>`;
  }).join("");
}

function populateVoyageDropdowns() {
  const filterSel = document.getElementById("filter-expense-voyage");
  if (filterSel) {
    filterSel.innerHTML = '<option value="">All Voyages</option>' + allVoyages.map(v => `<option value="${v.id}">${v.name}</option>`).join("");
  }

  const formSel = document.getElementById("expense-voyage");
  if (formSel) {
    formSel.innerHTML = allVoyages.map(v => `<option value="${v.id}">${v.name}</option>`).join("");
  }
}

function filterExpenses() {
  const search = (document.getElementById("expense-search").value || "").toLowerCase().trim();
  const voyageId = document.getElementById("filter-expense-voyage").value;
  const category = document.getElementById("filter-expense-category").value;

  let filtered = allExpenses.filter(e => {
    const desc = (e.description || "").toLowerCase();
    const cat = (e.category || "").toLowerCase();
    if (search && !desc.includes(search) && !cat.includes(search)) return false;
    if (voyageId && e.voyage_id !== parseInt(voyageId, 10)) return false;
    if (category && e.category !== category) return false;
    return true;
  });

  renderExpenseTable(filtered);
}

function openAddExpenseModal(preselectedVoyageId = null) {
  document.getElementById("expense-id").value = "";
  document.getElementById("expense-amount").value = "";
  document.getElementById("expense-date").value = new Date().toISOString().slice(0, 10);
  document.getElementById("expense-desc").value = "";

  if (preselectedVoyageId) {
    document.getElementById("expense-voyage").value = preselectedVoyageId;
  } else if (allVoyages.length) {
    document.getElementById("expense-voyage").value = allVoyages[0].id;
  }

  openModal("expense-modal");
}

async function saveExpense(e) {
  e.preventDefault();
  const voyageId = parseInt(document.getElementById("expense-voyage").value, 10);
  const category = document.getElementById("expense-category").value;
  const rawAmount = document.getElementById("expense-amount").value;
  const dateStr = document.getElementById("expense-date").value;
  const desc = document.getElementById("expense-desc").value.trim();

  const amountPaise = parseCurrencyToPaise(rawAmount);

  if (!voyageId) {
    showToast("Please select a valid voyage", "error");
    return;
  }
  if (!category) {
    showToast("Please select an expense category", "error");
    return;
  }
  if (!amountPaise || amountPaise <= 0) {
    showToast("Expense amount must be greater than zero", "error");
    return;
  }

  const payload = {
    voyage_id: voyageId,
    category: category,
    amount_paise: amountPaise,
    date: dateStr ? new Date(dateStr).toISOString() : new Date().toISOString(),
    description: desc || undefined
  };

  try {
    await API.createExpense(payload);
    showToast(`Expense of ${formatPaise(amountPaise)} logged to ledger!`, "success");
    closeModal("expense-modal");
    loadExpenses();
  } catch (err) {
    showToast(`Failed to record expense: ${err.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadExpenses();

  const addBtn = document.getElementById("add-expense-btn");
  if (addBtn) addBtn.addEventListener("click", () => openAddExpenseModal());

  const form = document.getElementById("expense-form");
  if (form) form.addEventListener("submit", saveExpense);

  const searchInput = document.getElementById("expense-search");
  if (searchInput) searchInput.addEventListener("input", filterExpenses);

  const voyageFilter = document.getElementById("filter-expense-voyage");
  if (voyageFilter) voyageFilter.addEventListener("change", filterExpenses);

  const catFilter = document.getElementById("filter-expense-category");
  if (catFilter) catFilter.addEventListener("change", filterExpenses);
});