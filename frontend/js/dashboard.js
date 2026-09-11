/**
 * Dashboard Logic for Captain's Treasure Ledger.
 * Pulls authoritative financial KPIs and metrics directly from the backend.
 */

let dashboardCharts = {};

async function loadDashboardData() {
  const kpiContainer = document.getElementById("kpi-cards");
  showSkeletonMetrics(kpiContainer, 6);

  try {
    // 1. Fetch Authoritative Dashboard KPI Snapshot
    const kpis = await API.getDashboardSummary();
    renderDashboardKPIs(kpis);

    // 2. Fetch Category Breakdown & Voyage Profitability for Charts
    const [catBreakdown, profitabilityRes, recentVoyages] = await Promise.all([
      API.getExpenseCategories().catch(() => []),
      API.getVoyagesProfitability({ page_size: 8 }).catch(() => ({ voyages: [] })),
      API.getVoyages({ page_size: 5 }).catch(() => [])
    ]);

    renderDashboardCharts(profitabilityRes.voyages || [], catBreakdown || []);
    renderRecentVoyages(recentVoyages || []);
  } catch (err) {
    console.error("Failed to load dashboard data:", err);
    showError(kpiContainer, "Could not load treasury summary from backend. Please verify FastAPI is running at http://127.0.0.1:8000.", loadDashboardData);
  }
}

function renderDashboardKPIs(kpis) {
  const c = document.getElementById("kpi-cards");
  if (!kpis) return;

  c.innerHTML = `
    <div class="metric-card metric--hero">
      <div class="metric-label">Total Revenue</div>
      <div class="metric-value">${formatPaise(kpis.total_revenue_paise)}</div>
      <div class="metric-sub">${kpis.completed_voyages || 0} completed voyages</div>
    </div>
    <div class="metric-card metric--warn">
      <div class="metric-label">Total Expenses</div>
      <div class="metric-value">${formatPaise(kpis.total_expenses_paise)}</div>
      <div class="metric-sub">Operating debits</div>
    </div>
    <div class="metric-card metric--positive">
      <div class="metric-label">Net Profit</div>
      <div class="metric-value">${formatPaise(kpis.net_profit_paise)}</div>
      <div class="metric-sub">Reconciled balance</div>
    </div>
    <div class="metric-card metric--gold">
      <div class="metric-label">Total Distributed</div>
      <div class="metric-value">${formatPaise(kpis.total_payouts_paise)}</div>
      <div class="metric-sub">Finalized dividends</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Active Crew</div>
      <div class="metric-value">${kpis.active_crew || 0}</div>
      <div class="metric-sub">Shareholding sailors</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Total Voyages</div>
      <div class="metric-value">${kpis.total_voyages || 0}</div>
      <div class="metric-sub">${kpis.ongoing_voyages || 0} active / ${kpis.planned_voyages || 0} planned</div>
    </div>`;
}

function renderDashboardCharts(voyages, categories) {
  // Destroy existing chart instances
  Object.values(dashboardCharts).forEach(c => { if (c && typeof c.destroy === "function") c.destroy(); });
  dashboardCharts = {};

  // 1. Revenue vs Expenses Bar Chart
  const revExpCanvas = document.getElementById("chart-rev-exp");
  if (revExpCanvas) {
    const labels = voyages.map(v => v.voyage_name || `Voyage #${v.voyage_id}`);
    const revData = voyages.map(v => (v.revenue_paise || 0) / 100);
    const expData = voyages.map(v => (v.expenses_paise || 0) / 100);

    dashboardCharts.revExp = new Chart(revExpCanvas, {
      type: "bar",
      data: {
        labels: labels.length ? labels : ["No Voyages Recorded"],
        datasets: [
          { label: "Revenue (₹)", data: revData.length ? revData : [0], backgroundColor: CHART_THEME.green, borderRadius: 4 },
          { label: "Expenses (₹)", data: expData.length ? expData : [0], backgroundColor: CHART_THEME.red, borderRadius: 4 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: CHART_THEME.legendColor, padding: 12, usePointStyle: true } },
          tooltip: CHART_THEME.tooltipStyle
        },
        scales: { ...CHART_THEME.baseScales }
      }
    });
  }

  // 2. Category Breakdown Doughnut Chart
  const catCanvas = document.getElementById("chart-expense-type");
  if (catCanvas) {
    const catLabels = categories.map(c => c.category);
    const catValues = categories.map(c => (c.amount_paise || 0) / 100);

    dashboardCharts.expenseCat = new Chart(catCanvas, {
      type: "doughnut",
      data: {
        labels: catLabels.length ? catLabels : ["No Expenses"],
        datasets: [{
          data: catValues.length ? catValues : [1],
          backgroundColor: [CHART_THEME.red, CHART_THEME.warn, CHART_THEME.gold, CHART_THEME.info, "#9b59b6", CHART_THEME.green],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { color: CHART_THEME.legendColor, padding: 14, usePointStyle: true } },
          tooltip: CHART_THEME.tooltipStyle
        }
      }
    });
  }

  // 3. Voyage Profitability Chart
  const profitCanvas = document.getElementById("chart-voyage-profit");
  if (profitCanvas) {
    const profitLabels = voyages.map(v => v.voyage_name || `Voyage #${v.voyage_id}`);
    const profitData = voyages.map(v => (v.net_profit_paise || 0) / 100);

    dashboardCharts.profitability = new Chart(profitCanvas, {
      type: "bar",
      data: {
        labels: profitLabels.length ? profitLabels : ["No Data"],
        datasets: [{
          label: "Net Profit (₹)",
          data: profitData.length ? profitData : [0],
          backgroundColor: profitData.map(v => v >= 0 ? CHART_THEME.gold : CHART_THEME.red),
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: CHART_THEME.tooltipStyle
        },
        scales: { ...CHART_THEME.baseScales }
      }
    });
  }
}

function renderRecentVoyages(voyages) {
  const container = document.getElementById("recent-voyages-body");
  if (!container) return;

  if (!voyages.length) {
    container.innerHTML = `<tr><td colspan="6" class="empty-row">No voyages recorded yet. Run <code>python -m backend.seed_demo</code> to seed demo data.</td></tr>`;
    return;
  }

  container.innerHTML = voyages.map(v => `
    <tr>
      <td class="td-name"><a href="voyages.html">${v.name}</a></td>
      <td>${formatDate(v.date)}</td>
      <td>${getStatusBadge(v.status)}</td>
      <td class="td-amount td-amount-green">${formatPaise(v.revenue_paise)}</td>
      <td class="td-actions">
        <button class="btn btn-secondary btn-sm" onclick="quickExport(${v.id}, 'json')">JSON</button>
        <button class="btn btn-secondary btn-sm" onclick="quickExport(${v.id}, 'csv')">CSV</button>
      </td>
    </tr>
  `).join("");
}

function quickExport(voyageId, format) {
  API.downloadExport(voyageId, format);
}

document.addEventListener("DOMContentLoaded", () => {
  loadDashboardData();
  
  const refreshBtn = document.getElementById("refresh-dashboard");
  if (refreshBtn) refreshBtn.addEventListener("click", loadDashboardData);

  const exportJsonBtn = document.getElementById("export-json");
  if (exportJsonBtn) exportJsonBtn.addEventListener("click", (e) => {
    e.preventDefault();
    API.getVoyages().then(voyages => {
      if (voyages.length) API.downloadExport(voyages[0].id, "json");
      else showToast("No voyages available to export", "warn");
    });
  });

  const exportCsvBtn = document.getElementById("export-csv");
  if (exportCsvBtn) exportCsvBtn.addEventListener("click", (e) => {
    e.preventDefault();
    API.getVoyages().then(voyages => {
      if (voyages.length) API.downloadExport(voyages[0].id, "csv");
      else showToast("No voyages available to export", "warn");
    });
  });
});