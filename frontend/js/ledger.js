let selectedCrewId = null;

async function loadLedger() {
  const crew = await API.getCrew();
  const sel = document.getElementById("ledger-crew-select");
  sel.innerHTML = '<option value="">Select Crew Member</option>' + crew.filter(c => c.status === "active").map(c => `<option value="${c.id}">${c.name}</option>`).join("");
}

function loadCrewLedger(crewId) {
  selectedCrewId = crewId;
  if (!crewId) {
    document.getElementById("ledger-kpis").style.display = "none";
    document.getElementById("ledger-timeline-container").innerHTML = `
      <div class="state">
        <div class="state-visual">
          <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v18H6.5A2.5 2.5 0 0 1 4 18.5v-13z"/><path d="M4 18.5A2.5 2.5 0 0 0 6.5 21H20"/></svg>
        </div>
        <h3>Select a crew member</h3>
        <p>Choose a crew member from the dropdown above to view their transaction history.</p>
      </div>`;
    return;
  }

  const crew = MOCK_CREW.find(c => c.id === parseInt(crewId));
  if (!crew) return;

  const rank = MOCK_RANKS.find(r => r.id === crew.rank_id);
  const payouts = MOCK_PAYOUTS.filter(p => p.crew_id === parseInt(crewId) && p.status === "paid");
  const totalEarned = payouts.reduce((s, p) => s + p.payout_paise, 0);
  const avgPayout = payouts.length ? Math.round(totalEarned / payouts.length) : 0;

  document.getElementById("ledger-kpis").style.display = "grid";
  document.getElementById("ledger-kpis").innerHTML = `
    <div class="metric-card metric--positive"><div class="metric-label">Current Balance</div><div class="metric-value">${formatCurrencyFull(totalEarned)}</div></div>
    <div class="metric-card metric--gold"><div class="metric-label">Total Earnings</div><div class="metric-value">${formatCurrencyFull(totalEarned)}</div></div>
    <div class="metric-card"><div class="metric-label">Voyages</div><div class="metric-value">${payouts.length}</div></div>
    <div class="metric-card"><div class="metric-label">Average Payout</div><div class="metric-value">${formatCurrencyFromPaise(avgPayout)}</div></div>`;

  const crewTransactions = MOCK_TRANSACTIONS.filter(t => t.crew_id === parseInt(crewId));
  const crewPayouts = MOCK_PAYOUTS.filter(p => p.crew_id === parseInt(crewId));

  const allEntries = [
    ...crewPayouts.map(p => {
      const v = MOCK_VOYAGES.find(x => x.id === p.voyage_id);
      return { date: p.date, type: "payout", description: "Crew Dividend", amount: p.payout_paise, voyage: v ? v.name : "Unknown", time: "02:00 PM", sortTime: 1400 };
    })
  ].sort((a, b) => b.date.localeCompare(a.date) || b.sortTime - a.sortTime);

  const container = document.getElementById("ledger-timeline-container");
  if (!allEntries.length) {
    container.innerHTML = `
      <div class="state">
        <div class="state-visual">${icon('ledger')}</div>
        <h3>No transactions yet</h3>
        <p>${crew.name} has no recorded transactions.</p>
      </div>`;
    return;
  }

  let html = '<div class="timeline">';
  let lastDate = "";
  allEntries.forEach(e => {
    if (e.date !== lastDate) {
      html += `<div class="timeline-date">${formatDate(e.date)}</div>`;
      lastDate = e.date;
    }
    const isDebit = e.type === "debit";
    const isCredit = e.type === "credit";
    const amountPrefix = isDebit ? "\u2212" : "+";
    const amountClass = isCredit ? "tl-green" : isDebit ? "tl-red" : "tl-gold";
    const nodeIcon = isCredit ? 'flag' : isDebit ? 'alert' : 'coin';
    html += `
      <div class="timeline-entry">
        <div class="timeline-node timeline-node-${e.type}">${icon(nodeIcon, 14)}</div>
        <div class="timeline-card">
          <div class="timeline-card-head">
            <span class="timeline-type">${e.type.toUpperCase()}</span>
            <span class="timeline-time">${e.time}</span>
          </div>
          <div class="timeline-card-body">
            <div class="timeline-desc">${e.description}</div>
            <div class="timeline-voyage">${e.voyage}</div>
          </div>
          <div class="timeline-amount ${amountClass}">${amountPrefix}${formatCurrencyFull(e.amount)}</div>
        </div>
      </div>`;
  });
  html += '</div>';
  container.innerHTML = html;
}

document.addEventListener("DOMContentLoaded", () => {
  initCommon();
  loadLedger();
  document.getElementById("ledger-crew-select").addEventListener("change", (e) => {
    loadCrewLedger(e.target.value);
  });
});