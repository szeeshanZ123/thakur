let analyticsCharts = {};

async function loadAnalytics() {
  const analytics = await API.getAnalytics();
  renderAnalyticsKPIs(analytics);
  renderAnalyticsCharts(analytics);
  renderRankSettings();
}

function renderAnalyticsKPIs(a) {
  document.getElementById("analytics-kpis").innerHTML = `
    <div class="metric-card metric--positive"><div class="metric-label">Total Profit</div><div class="metric-value">${formatCurrencyFromPaise(a.total_profit)}</div></div>
    <div class="metric-card"><div class="metric-label">Average Profit</div><div class="metric-value">${formatCurrencyFromPaise(a.avg_profit)}</div></div>
    <div class="metric-card metric--gold"><div class="metric-label">Highest Profit Voyage</div><div class="metric-value metric-value-sm">${a.highest_profit_voyage.name}<br><span class="metric-sub td-amount-green">${formatCurrencyFromPaise(a.highest_profit_voyage.profit)}</span></div></div>
    <div class="metric-card"><div class="metric-label">Avg Profit Margin</div><div class="metric-value">${(a.avg_profit_margin_bps / 100).toFixed(1)}%</div></div>
    <div class="metric-card metric--warn"><div class="metric-label">Expense Ratio</div><div class="metric-value">${(a.expense_ratio_bps / 100).toFixed(1)}%</div></div>`;
}

function renderAnalyticsCharts(a) {
  Object.values(analyticsCharts).forEach(c => c.destroy());
  analyticsCharts = {};

  const chartOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: CHART_THEME.legendColor, padding: 16, usePointStyle: true, pointStyleWidth: 10 } },
      tooltip: CHART_THEME.tooltipStyle
    },
    scales: {
      x: { ticks: { color: CHART_THEME.tickColor, font: { size: 11 } }, grid: { color: CHART_THEME.gridColor }, border: { color: "rgba(64,55,43,0.4)" } },
      y: { ticks: { color: CHART_THEME.tickColor, font: { size: 11 } }, grid: { color: CHART_THEME.gridColor }, border: { display: false } }
    }
  };

  const monthLabels = Object.keys(a.revenue_by_month).sort();
  const revenueData = monthLabels.map(m => (a.revenue_by_month[m] || 0) / 100);
  const expenseData = monthLabels.map(m => (a.expenses_by_month[m] || 0) / 100);

  analyticsCharts.revTrend = new Chart(document.getElementById("chart-rev-trend"), {
    type: "line",
    data: {
      labels: monthLabels,
      datasets: [{ label: "Revenue", data: revenueData, borderColor: CHART_THEME.green, backgroundColor: "rgba(79,164,91,0.1)", fill: true, tension: 0.35, pointRadius: 3, pointHoverRadius: 6 }]
    },
    options: chartOpts
  });

  analyticsCharts.expTrend = new Chart(document.getElementById("chart-exp-trend"), {
    type: "line",
    data: {
      labels: monthLabels,
      datasets: [{ label: "Expenses", data: expenseData, borderColor: CHART_THEME.red, backgroundColor: "rgba(216,74,63,0.1)", fill: true, tension: 0.35, pointRadius: 3, pointHoverRadius: 6 }]
    },
    options: chartOpts
  });

  const vLabels = a.voyage_data.map(v => v.name);
  analyticsCharts.revExpBar = new Chart(document.getElementById("chart-rev-exp-bar"), {
    type: "bar",
    data: {
      labels: vLabels,
      datasets: [
        { label: "Revenue", data: a.voyage_data.map(v => v.revenue / 100), backgroundColor: CHART_THEME.green, borderRadius: 4 },
        { label: "Expenses", data: a.voyage_data.map(v => v.expenses / 100), backgroundColor: CHART_THEME.red, borderRadius: 4 }
      ]
    },
    options: chartOpts
  });

  const expBreakdown = a.expense_breakdown;
  analyticsCharts.expDoughnut = new Chart(document.getElementById("chart-exp-doughnut"), {
    type: "doughnut",
    data: {
      labels: Object.keys(expBreakdown),
      datasets: [{ data: Object.values(expBreakdown).map(v => v / 100), backgroundColor: [CHART_THEME.red, CHART_THEME.warn, CHART_THEME.green, CHART_THEME.info, "#9b59b6", CHART_THEME.goldLight], borderWidth: 0 }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: CHART_THEME.legendColor, padding: 16, usePointStyle: true, pointStyleWidth: 10 } }, tooltip: CHART_THEME.tooltipStyle } }
  });

  analyticsCharts.profitVoyage = new Chart(document.getElementById("chart-profit-voyage"), {
    type: "bar",
    data: {
      labels: vLabels,
      datasets: [{ label: "Net Profit", data: a.voyage_data.map(v => v.profit / 100), backgroundColor: a.voyage_data.map(v => v.profit >= 0 ? CHART_THEME.green : CHART_THEME.red), borderRadius: 4 }]
    },
    options: { ...chartOpts, plugins: { legend: { display: false }, tooltip: CHART_THEME.tooltipStyle } }
  });

  const crewNames = a.crew_earnings.map(c => c.name);
  const crewEarned = a.crew_earnings.map(c => c.total_earned / 100);
  analyticsCharts.crewEarnings = new Chart(document.getElementById("chart-crew-earnings"), {
    type: "bar",
    data: {
      labels: crewNames,
      datasets: [{ label: "Total Earned", data: crewEarned, backgroundColor: CHART_THEME.gold, borderRadius: 4 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      indexAxis: "y",
      plugins: { legend: { display: false }, tooltip: CHART_THEME.tooltipStyle },
      scales: {
        x: { ticks: { color: CHART_THEME.tickColor }, grid: { color: CHART_THEME.gridColor }, border: { display: false } },
        y: { ticks: { color: CHART_THEME.tickColor }, grid: { color: "rgba(64,55,43,0.18)" }, border: { color: "rgba(64,55,43,0.4)" } }
      }
    }
  });
}

function renderRankSettings() {
  document.getElementById("rank-settings-list").innerHTML = MOCK_RANKS.map(r => `
    <div class="rank-row">
      <div class="rank-info">
        <span class="rank-name">${r.name}</span>
        <span class="rank-status">${getStatusBadge(r.status)}</span>
      </div>
      <span class="rank-weight">${shareWeightToDisplay(r.share_weight_units)}</span>
    </div>`).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  initCommon();
  loadAnalytics();
  document.getElementById("analytics-period").addEventListener("change", () => { loadAnalytics(); showToast("Period filter applied (mock)", "info"); });
});