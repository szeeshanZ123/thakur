let charts = {};

async function loadDashboardData() {
  const kpis = await API.getDashboardKPIs();
  renderKPIs(kpis);
  const analytics = await API.getAnalytics();
  renderCharts(analytics);
  renderInsights();
}

function renderKPIs(kpis) {
  const c = document.getElementById("kpi-cards");
  c.innerHTML = `
    <div class="metric-card metric--hero">
      <div class="metric-label">Total Revenue</div>
      <div class="metric-value">${formatCurrencyFromPaise(kpis.total_revenue_paise)}</div>
    </div>
    <div class="metric-card metric--warn">
      <div class="metric-label">Total Expenses</div>
      <div class="metric-value">${formatCurrencyFromPaise(kpis.total_expenses_paise)}</div>
    </div>
    <div class="metric-card metric--positive">
      <div class="metric-label">Net Profit</div>
      <div class="metric-value">${formatCurrencyFromPaise(kpis.net_profit_paise)}</div>
    </div>
    <div class="metric-card metric--gold">
      <div class="metric-label">Total Distributed</div>
      <div class="metric-value">${formatCurrencyFromPaise(kpis.total_distributed_paise)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Active Crew</div>
      <div class="metric-value">${kpis.active_crew}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Completed Voyages</div>
      <div class="metric-value">${kpis.completed_voyages}</div>
    </div>`;
}

function renderCharts(analytics) {
  Object.values(charts).forEach(c => c.destroy());
  charts = {};

  const labels = analytics.voyage_data.map(v => v.name);
  const revenue = analytics.voyage_data.map(v => v.revenue / 100);
  const expenses = analytics.voyage_data.map(v => v.expenses / 100);
  const profit = analytics.voyage_data.map(v => v.profit / 100);

  charts.revExp = new Chart(document.getElementById("chart-rev-exp"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Revenue", data: revenue, backgroundColor: CHART_THEME.green, borderRadius: 4 },
        { label: "Expenses", data: expenses, backgroundColor: CHART_THEME.red, borderRadius: 4 },
        { label: "Net Profit", data: profit, backgroundColor: CHART_THEME.gold, borderRadius: 4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: CHART_THEME.legendColor, padding: 16, usePointStyle: true, pointStyleWidth: 10 } },
        tooltip: CHART_THEME.tooltipStyle
      },
      scales: { ...CHART_THEME.baseScales }
    }
  });

  const expBreakdown = analytics.expense_breakdown;
  charts.expenseType = new Chart(document.getElementById("chart-expense-type"), {
    type: "doughnut",
    data: {
      labels: Object.keys(expBreakdown),
      datasets: [{
        data: Object.values(expBreakdown).map(v => v / 100),
        backgroundColor: [CHART_THEME.red, CHART_THEME.warn, CHART_THEME.green, CHART_THEME.info, "#9b59b6", CHART_THEME.goldLight],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: CHART_THEME.legendColor, padding: 16, usePointStyle: true, pointStyleWidth: 10 } },
        tooltip: CHART_THEME.tooltipStyle
      }
    }
  });

  charts.voyageProfit = new Chart(document.getElementById("chart-voyage-profit"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Net Profit",
        data: profit,
        backgroundColor: profit.map(v => v >= 0 ? CHART_THEME.green : CHART_THEME.red),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: CHART_THEME.tooltipStyle },
      scales: { ...CHART_THEME.baseScales }
    }
  });
}

function renderInsights() {
  const grid = document.getElementById("insights-grid");
  grid.innerHTML = MOCK_INSIGHTS.map(i => `
    <div class="insight-card insight-${i.type}">
      <div class="insight-icon">${icon(i.icon)}</div>
      <div class="insight-body">
        <h4>${i.title}</h4>
        <p>${i.text}</p>
        ${i.action ? `<button class="btn-link" onclick="showToast('${i.action} — coming soon', 'info')">${i.action}</button>` : ''}
      </div>
    </div>`).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  initCommon();
  loadDashboardData();
  document.getElementById("load-sample").addEventListener("click", () => { showToast("Sample voyage data loaded!", "success"); });
  document.getElementById("export-json").addEventListener("click", (e) => { e.preventDefault(); exportManifest("json"); });
  document.getElementById("export-csv").addEventListener("click", (e) => { e.preventDefault(); exportManifest("csv"); });
});