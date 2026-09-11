/**
 * Analytics Dashboard JavaScript for Captain's Treasure Ledger.
 * Integrates live FastAPI backend analytics endpoints to visualize revenue,
 * expense breakdowns, voyage profitability, and crew dividend distributions via Chart.js.
 * 
 * Invariant: All financial aggregations come directly from backend.
 */

let analyticsCharts = {};

async function loadAnalytics() {
  const kpiContainer = document.getElementById("analytics-kpis");
  if (kpiContainer) {
    kpiContainer.innerHTML = '<div class="loading-cell" style="grid-column:1/-1;">Loading fleet intelligence metrics from backend...</div>';
  }

  try {
    const [
      dashboardData,
      profitData,
      expenseCatData,
      voyagesProfData,
      crewEarnData,
      rankPayoutsData
    ] = await Promise.all([
      API.getAnalyticsDashboard(),
      API.getProfitAnalytics(),
      API.getExpenseCategories(),
      API.getVoyagesProfitability(),
      API.getCrewEarnings(),
      API.getRankPayouts()
    ]);

    renderAnalyticsKPIs(dashboardData, profitData);
    const expCategories = expenseCatData?.items || (Array.isArray(expenseCatData) ? expenseCatData : []);
    const voyProfitability = voyagesProfData?.items || voyagesProfData?.voyages || (Array.isArray(voyagesProfData) ? voyagesProfData : []);
    const crewEarnings = crewEarnData?.items || crewEarnData?.crew || (Array.isArray(crewEarnData) ? crewEarnData : []);
    const rankPayouts = rankPayoutsData?.ranks || (Array.isArray(rankPayoutsData) ? rankPayoutsData : []);

    renderAnalyticsCharts({
      dashboard: dashboardData,
      profit: profitData,
      expenseCategories: expCategories,
      voyagesProfitability: voyProfitability,
      crewEarnings: crewEarnings,
      rankPayouts: rankPayouts
    });

    renderRankedTables({
      voyages: voyProfitability,
      crew: crewEarnings
    });
  } catch (err) {
    console.error("Failed to load analytics:", err);
    showToast(`Failed to load analytics: ${err.message}`, "error");
    if (kpiContainer) {
      kpiContainer.innerHTML = `<div class="alert alert-danger" style="grid-column:1/-1;">Could not fetch analytics from backend. Error: ${err.message}</div>`;
    }
  }
}

function renderAnalyticsKPIs(dash, profit) {
  const container = document.getElementById("analytics-kpis");
  if (!container) return;

  const marginPct = (profit.average_profit_margin_basis_points / 100).toFixed(1);
  const isProfit = (dash.net_profit_paise || 0) >= 0;

  container.innerHTML = `
    <div class="metric-card">
      <div class="metric-label">Gross Revenue</div>
      <div class="metric-value">${formatPaise(dash.total_revenue_paise || 0)}</div>
      <div class="metric-sub">${dash.total_voyages || 0} Total Voyages</div>
    </div>
    <div class="metric-card metric--warn">
      <div class="metric-label">Operational Expenses</div>
      <div class="metric-value">${formatPaise(dash.total_expenses_paise || 0)}</div>
      <div class="metric-sub">Fleet Outfitting & Provisions</div>
    </div>
    <div class="metric-card ${isProfit ? 'metric--positive' : 'metric--danger'}">
      <div class="metric-label">Net Profit</div>
      <div class="metric-value">${formatPaise(dash.net_profit_paise || 0)}</div>
      <div class="metric-sub">${marginPct}% Avg Margin</div>
    </div>
    <div class="metric-card metric--gold">
      <div class="metric-label">Distributable Dividends</div>
      <div class="metric-value">${formatPaise(dash.distributable_profit_paise || 0)}</div>
      <div class="metric-sub">${formatPaise(dash.total_payouts_paise || 0)} Finalized</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Fleet Success Rate</div>
      <div class="metric-value">${profit.profitable_voyages || 0} / ${dash.total_voyages || 0}</div>
      <div class="metric-sub">${profit.loss_making_voyages || 0} Loss-Making</div>
    </div>
  `;
}

function renderAnalyticsCharts(data) {
  // Destroy existing chart instances cleanly
  Object.values(analyticsCharts).forEach(c => {
    if (c && typeof c.destroy === "function") c.destroy();
  });
  analyticsCharts = {};

  const baseChartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: CHART_THEME.legendColor,
          padding: 14,
          usePointStyle: true,
          pointStyleWidth: 8,
          font: { family: "'Inter', sans-serif", size: 12 }
        }
      },
      tooltip: {
        ...CHART_THEME.tooltipStyle,
        callbacks: {
          label: function(context) {
            const label = context.dataset.label || context.label || '';
            const val = context.raw || 0;
            return ` ${label}: ₹${Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
          }
        }
      }
    },
    scales: {
      x: {
        ticks: { color: CHART_THEME.tickColor, font: { size: 11 } },
        grid: { color: CHART_THEME.gridColor }
      },
      y: {
        ticks: {
          color: CHART_THEME.tickColor,
          font: { size: 11 },
          callback: v => `₹${Number(v).toLocaleString("en-IN")}`
        },
        grid: { color: CHART_THEME.gridColor }
      }
    }
  };

  // 1. Revenue vs Expenses Bar Chart
  const voyages = data.voyagesProfitability || [];
  const vNames = voyages.map(v => v.voyage_name);
  const vRevs = voyages.map(v => (v.revenue_paise || 0) / 100);
  const vExps = voyages.map(v => (v.expenses_paise || 0) / 100);

  const revExpEl = document.getElementById("chart-rev-exp-bar");
  if (revExpEl) {
    analyticsCharts.revExpBar = new Chart(revExpEl, {
      type: "bar",
      data: {
        labels: vNames.length ? vNames : ["No Voyages"],
        datasets: [
          {
            label: "Gross Revenue",
            data: vRevs.length ? vRevs : [0],
            backgroundColor: CHART_THEME.green,
            borderRadius: 4
          },
          {
            label: "Expenses",
            data: vExps.length ? vExps : [0],
            backgroundColor: CHART_THEME.red,
            borderRadius: 4
          }
        ]
      },
      options: baseChartOpts
    });
  }

  // 2. Expense Category Breakdown (Doughnut)
  const expCats = data.expenseCategories || [];
  const catLabels = expCats.map(c => c.category);
  const catAmounts = expCats.map(c => (c.amount_paise || 0) / 100);

  const expDoughnutEl = document.getElementById("chart-exp-doughnut");
  if (expDoughnutEl) {
    analyticsCharts.expDoughnut = new Chart(expDoughnutEl, {
      type: "doughnut",
      data: {
        labels: catLabels.length ? catLabels : ["No Expenses"],
        datasets: [{
          data: catAmounts.length ? catAmounts : [1],
          backgroundColor: [
            CHART_THEME.gold,
            CHART_THEME.red,
            CHART_THEME.warn,
            CHART_THEME.info,
            "#8b5cf6",
            "#ec4899"
          ],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: CHART_THEME.legendColor,
              padding: 12,
              usePointStyle: true,
              font: { size: 11 }
            }
          },
          tooltip: {
            ...CHART_THEME.tooltipStyle,
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const val = context.raw || 0;
                return ` ${label}: ₹${Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
              }
            }
          }
        }
      }
    });
  }

  // 3. Voyage Profitability (Net Profit)
  const vProfits = voyages.map(v => (v.net_profit_paise || 0) / 100);
  const profitEl = document.getElementById("chart-profit-voyage");
  if (profitEl) {
    analyticsCharts.profitVoyage = new Chart(profitEl, {
      type: "bar",
      data: {
        labels: vNames.length ? vNames : ["No Voyages"],
        datasets: [{
          label: "Net Profit",
          data: vProfits.length ? vProfits : [0],
          backgroundColor: vProfits.map(p => p >= 0 ? CHART_THEME.green : CHART_THEME.red),
          borderRadius: 4
        }]
      },
      options: {
        ...baseChartOpts,
        plugins: {
          ...baseChartOpts.plugins,
          legend: { display: false }
        }
      }
    });
  }

  // 4. Crew Earnings (Horizontal Bar Chart)
  const crew = data.crewEarnings || [];
  const topCrew = [...crew].sort((a, b) => b.total_earnings_paise - a.total_earnings_paise).slice(0, 8);
  const crewNames = topCrew.map(c => `${c.name} (${c.rank})`);
  const crewAmounts = topCrew.map(c => (c.total_earnings_paise || 0) / 100);

  const crewEl = document.getElementById("chart-crew-earnings");
  if (crewEl) {
    analyticsCharts.crewEarnings = new Chart(crewEl, {
      type: "bar",
      data: {
        labels: crewNames.length ? crewNames : ["No Crew Distributions"],
        datasets: [{
          label: "Lifetime Dividends",
          data: crewAmounts.length ? crewAmounts : [0],
          backgroundColor: CHART_THEME.gold,
          borderRadius: 4
        }]
      },
      options: {
        ...baseChartOpts,
        indexAxis: "y",
        plugins: {
          ...baseChartOpts.plugins,
          legend: { display: false }
        },
        scales: {
          x: {
            ticks: {
              color: CHART_THEME.tickColor,
              callback: v => `₹${Number(v).toLocaleString("en-IN")}`
            },
            grid: { color: CHART_THEME.gridColor }
          },
          y: {
            ticks: { color: CHART_THEME.tickColor, font: { size: 11 } },
            grid: { display: false }
          }
        }
      }
    });
  }

  // 5. Rank-wise Dividend Distribution
  const rankPayouts = data.rankPayouts || [];
  const rankLabels = rankPayouts.map(r => `${r.rank} (${shareWeightToDisplay(r.share_weight_units)})`);
  const rankAmounts = rankPayouts.map(r => (r.total_payout_paise || 0) / 100);

  const rankEl = document.getElementById("chart-rank-payouts");
  if (rankEl) {
    analyticsCharts.rankPayouts = new Chart(rankEl, {
      type: "doughnut",
      data: {
        labels: rankLabels.length ? rankLabels : ["No Payouts"],
        datasets: [{
          data: rankAmounts.length ? rankAmounts : [1],
          backgroundColor: [
            CHART_THEME.gold,
            CHART_THEME.green,
            CHART_THEME.info,
            "#a855f7",
            "#f97316"
          ],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: CHART_THEME.legendColor,
              padding: 10,
              usePointStyle: true,
              font: { size: 11 }
            }
          },
          tooltip: {
            ...CHART_THEME.tooltipStyle,
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const val = context.raw || 0;
                return ` ${label}: ₹${Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
              }
            }
          }
        }
      }
    });
  }
}

function renderRankedTables(data) {
  // Top Performing Voyages
  const topVoyagesBody = document.getElementById("top-voyages-table-body");
  if (topVoyagesBody) {
    const sortedVoyages = [...(data.voyages || [])].sort((a, b) => b.net_profit_paise - a.net_profit_paise);
    if (!sortedVoyages.length) {
      topVoyagesBody.innerHTML = '<tr><td colspan="5" class="empty-row">No expedition records available.</td></tr>';
    } else {
      topVoyagesBody.innerHTML = sortedVoyages.slice(0, 5).map((v, i) => `
        <tr>
          <td><span class="rank-badge rank-${i+1}">#${i+1}</span> <strong>${v.voyage_name}</strong></td>
          <td>${formatDate(v.date)}</td>
          <td class="td-amount td-amount-green">${formatPaise(v.revenue_paise)}</td>
          <td class="td-amount td-amount-red">${formatPaise(v.expenses_paise)}</td>
          <td class="td-amount ${v.net_profit_paise >= 0 ? 'td-amount-green' : 'td-amount-red'}">
            <strong>${formatPaise(v.net_profit_paise)}</strong>
          </td>
        </tr>
      `).join("");
    }
  }

  // Highest Earning Crew
  const crewBody = document.getElementById("top-crew-table-body");
  if (crewBody) {
    const sortedCrew = [...(data.crew || [])].sort((a, b) => b.total_earnings_paise - a.total_earnings_paise);
    if (!sortedCrew.length) {
      crewBody.innerHTML = '<tr><td colspan="4" class="empty-row">No crew dividend distributions recorded.</td></tr>';
    } else {
      crewBody.innerHTML = sortedCrew.slice(0, 5).map((c, i) => `
        <tr>
          <td><span class="rank-badge rank-${i+1}">#${i+1}</span> <strong>${c.name}</strong></td>
          <td><span class="badge badge-gold">${c.rank}</span></td>
          <td>${c.payout_count} Voyage(s)</td>
          <td class="td-amount td-amount-gold"><strong>${formatPaise(c.total_earnings_paise)}</strong></td>
        </tr>
      `).join("");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadAnalytics();
});