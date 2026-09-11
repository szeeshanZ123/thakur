const API = {
  async getRanks() { return [...MOCK_RANKS]; },
  async getCrew() { return [...MOCK_CREW]; },
  async getCrewById(id) { return MOCK_CREW.find(c => c.id === id) || null; },
  async getVoyages() { return [...MOCK_VOYAGES]; },
  async getVoyageById(id) { return MOCK_VOYAGES.find(v => v.id === id) || null; },
  async getExpenses() { return [...MOCK_EXPENSES]; },
  async getExpensesByVoyage(voyageId) { return MOCK_EXPENSES.filter(e => e.voyage_id === voyageId); },
  async getTransactions() { return [...MOCK_TRANSACTIONS]; },
  async getTransactionsByCrew(crewId) { return MOCK_TRANSACTIONS.filter(t => t.crew_id === crewId); },
  async getTransactionsByVoyage(voyageId) { return MOCK_TRANSACTIONS.filter(t => t.voyage_id === voyageId); },
  async getPayouts() { return [...MOCK_PAYOUTS]; },
  async getPayoutsByVoyage(voyageId) { return MOCK_PAYOUTS.filter(p => p.voyage_id === voyageId); },
  async getPayoutsByCrew(crewId) { return MOCK_PAYOUTS.filter(p => p.crew_id === crewId); },
  async getDashboardKPIs() {
    const revenue = MOCK_VOYAGES.filter(v => v.status === "completed").reduce((s, v) => s + v.revenue_paise, 0);
    const expenses = MOCK_EXPENSES.reduce((s, e) => s + e.amount_paise, 0);
    const paid = MOCK_PAYOUTS.filter(p => p.status === "paid").reduce((s, p) => s + p.payout_paise, 0);
    const activeCrew = MOCK_CREW.filter(c => c.status === "active").length;
    const completedVoyages = MOCK_VOYAGES.filter(v => v.status === "completed").length;
    return {
      total_revenue_paise: revenue,
      total_expenses_paise: expenses,
      net_profit_paise: revenue - expenses,
      total_distributed_paise: paid,
      active_crew: activeCrew,
      completed_voyages: completedVoyages
    };
  },
  async getAnalytics() {
    const completed = MOCK_VOYAGES.filter(v => v.status === "completed");
    const voyageData = completed.map(v => {
      const exp = MOCK_EXPENSES.filter(e => e.voyage_id === v.id).reduce((s, e) => s + e.amount_paise, 0);
      return { name: v.name, revenue: v.revenue_paise, expenses: exp, profit: v.revenue_paise - exp };
    });
    const totalProfit = voyageData.reduce((s, v) => s + v.profit, 0);
    const avgProfit = voyageData.length ? totalProfit / voyageData.length : 0;
    const highest = voyageData.reduce((max, v) => v.profit > max.profit ? v : max, voyageData[0] || { name: "N/A", profit: 0 });
    const totalRev = voyageData.reduce((s, v) => s + v.revenue, 0);
    const avgMargin = totalRev ? (totalProfit / totalRev * 10000) : 0;
    const totalExp = voyageData.reduce((s, v) => s + v.expenses, 0);
    const expenseRatio = totalRev ? (totalExp / totalRev * 10000) : 0;
    const expenseBreakdown = {};
    MOCK_EXPENSES.forEach(e => {
      expenseBreakdown[e.category] = (expenseBreakdown[e.category] || 0) + e.amount_paise;
    });
    const crewEarnings = MOCK_CREW.filter(c => c.status === "active").map(c => {
      const rank = MOCK_RANKS.find(r => r.id === c.rank_id);
      const paid = MOCK_PAYOUTS.filter(p => p.crew_id === c.id && p.status === "paid").reduce((s, p) => s + p.payout_paise, 0);
      return { name: c.name, rank: rank ? rank.name : "Unknown", total_earned: paid };
    });
    const revenueByMonth = {};
    completed.forEach(v => {
      const m = v.date.substring(0, 7);
      revenueByMonth[m] = (revenueByMonth[m] || 0) + v.revenue_paise;
    });
    const expensesByMonth = {};
    MOCK_EXPENSES.forEach(e => {
      const m = e.date.substring(0, 7);
      expensesByMonth[m] = (expensesByMonth[m] || 0) + e.amount_paise;
    });
    return {
      voyage_data: voyageData,
      total_profit: totalProfit,
      avg_profit: Math.round(avgProfit),
      highest_profit_voyage: highest,
      avg_profit_margin_bps: Math.round(avgMargin),
      expense_ratio_bps: Math.round(expenseRatio),
      expense_breakdown: expenseBreakdown,
      crew_earnings: crewEarnings,
      revenue_by_month: revenueByMonth,
      expenses_by_month: expensesByMonth
    };
  }
};
