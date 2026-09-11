let allCrew = [];

async function loadCrew() {
  allCrew = await API.getCrew();
  renderCrewKPIs(allCrew);
  renderCrewTable(allCrew);
  populateRankFilter();
  populateAddFormRanks();
}

function renderCrewKPIs(crew) {
  const active = crew.filter(c => c.status === "active").length;
  const inactive = crew.filter(c => c.status === "inactive").length;
  const earnings = crew.map(c => {
    const paid = MOCK_PAYOUTS.filter(p => p.crew_id === c.id && p.status === "paid").reduce((s, p) => s + p.payout_paise, 0);
    return { name: c.name, earned: paid };
  });
  const top = earnings.reduce((max, e) => e.earned > max.earned ? e : max, { name: "N/A", earned: 0 });
  document.getElementById("crew-kpis").innerHTML = `
    <div class="metric-card"><div class="metric-label">Total Crew</div><div class="metric-value">${crew.length}</div></div>
    <div class="metric-card metric--positive"><div class="metric-label">Active Crew</div><div class="metric-value">${active}</div></div>
    <div class="metric-card metric--warn"><div class="metric-label">Inactive Crew</div><div class="metric-value">${inactive}</div></div>
    <div class="metric-card metric--gold"><div class="metric-label">Highest Earner</div><div class="metric-value metric-value-sm">${top.name}<br><span class="metric-sub">${formatCurrencyFromPaise(top.earned)}</span></div></div>`;
}

function renderCrewTable(crew) {
  const tbody = document.getElementById("crew-table-body");
  if (!crew.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-row">No crew members found.</td></tr>';
    return;
  }
  tbody.innerHTML = crew.map(c => {
    const rank = MOCK_RANKS.find(r => r.id === c.rank_id);
    const earned = MOCK_PAYOUTS.filter(p => p.crew_id === c.id && p.status === "paid").reduce((s, p) => s + p.payout_paise, 0);
    return `<tr>
      <td class="td-id" data-label="ID">#${String(c.id).padStart(3,"0")}</td>
      <td class="td-name" data-label="Crew Member">${c.name}</td>
      <td data-label="Rank">${rank ? rank.name : "Unknown"}</td>
      <td class="td-share" data-label="Share Weight">${shareWeightToDisplay(rank ? rank.share_weight_units : 0)}</td>
      <td data-label="Status">${getStatusBadge(c.status)}</td>
      <td class="td-amount" data-label="Total Earnings">${formatCurrencyFull(earned)}</td>
      <td class="td-actions" data-label="Actions">
        <button class="btn-icon" onclick="viewCrewProfile(${c.id})" title="View Profile">${icon('eye', 16)}</button>
      </td>
    </tr>`;
  }).join("");
}

function populateRankFilter() {
  const sel = document.getElementById("filter-rank");
  sel.innerHTML = '<option value="">All Ranks</option>' + MOCK_RANKS.map(r => `<option value="${r.id}">${r.name}</option>`).join("");
}

function populateAddFormRanks() {
  const sel = document.getElementById("crew-rank");
  sel.innerHTML = MOCK_RANKS.map(r => `<option value="${r.id}">${r.name} (${shareWeightToDisplay(r.share_weight_units)})</option>`).join("");
  sel.addEventListener("change", () => {
    const rank = MOCK_RANKS.find(r => r.id === parseInt(sel.value));
    document.getElementById("crew-share-display").value = rank ? shareWeightToDisplay(rank.share_weight_units) : "Select a rank";
  });
  sel.dispatchEvent(new Event("change"));
}

function filterCrew() {
  const search = document.getElementById("crew-search").value.toLowerCase();
  const rankId = document.getElementById("filter-rank").value;
  const status = document.getElementById("filter-status").value;
  let filtered = allCrew.filter(c => {
    if (search && !c.name.toLowerCase().includes(search)) return false;
    if (rankId && c.rank_id !== parseInt(rankId)) return false;
    if (status && c.status !== status) return false;
    return true;
  });
  renderCrewTable(filtered);
}

function viewCrewProfile(crewId) {
  const c = allCrew.find(m => m.id === crewId);
  if (!c) return;
  const rank = MOCK_RANKS.find(r => r.id === c.rank_id);
  const payouts = MOCK_PAYOUTS.filter(p => p.crew_id === c.id && p.status === "paid");
  const totalEarned = payouts.reduce((s, p) => s + p.payout_paise, 0);
  const avgPayout = payouts.length ? Math.round(totalEarned / payouts.length) : 0;

  document.getElementById("profile-name").textContent = c.name;
  document.getElementById("profile-body").innerHTML = `
    <div style="margin-bottom:20px">
      <div class="detail-grid">
        <div class="detail-item"><span class="detail-label">Rank</span><span class="detail-value">${rank ? rank.name : "Unknown"}</span></div>
        <div class="detail-item"><span class="detail-label">Share Weight</span><span class="detail-value td-share">${shareWeightToDisplay(rank ? rank.share_weight_units : 0)}</span></div>
        <div class="detail-item"><span class="detail-label">Status</span><span class="detail-value">${getStatusBadge(c.status)}</span></div>
      </div>
    </div>
    <div class="kpi-grid" style="margin-bottom:20px">
      <div class="metric-card"><div class="metric-label">Total Earnings</div><div class="metric-value metric--positive">${formatCurrencyFull(totalEarned)}</div></div>
      <div class="metric-card"><div class="metric-label">Voyages</div><div class="metric-value">${payouts.length}</div></div>
      <div class="metric-card"><div class="metric-label">Avg Payout</div><div class="metric-value">${formatCurrencyFromPaise(avgPayout)}</div></div>
    </div>
    <h4 class="section-subtitle">Earnings History</h4>
    <div class="table-shell">
      <table>
        <thead><tr><th>Voyage</th><th>Date</th><th>Payout</th><th>Status</th></tr></thead>
        <tbody>
          ${payouts.length ? payouts.map(p => {
            const v = MOCK_VOYAGES.find(v => v.id === p.voyage_id);
            return `<tr>
              <td class="td-name" data-label="Voyage">${v ? v.name : "Unknown"}</td>
              <td data-label="Date">${formatDate(p.date)}</td>
              <td class="td-amount td-amount-green" data-label="Payout">${formatCurrencyFull(p.payout_paise)}</td>
              <td data-label="Status">${getStatusBadge(p.status)}</td>
            </tr>`;
          }).join("") : '<tr><td colspan="4" class="empty-row">No payouts recorded yet.</td></tr>'}
        </tbody>
      </table>
    </div>`;
  openModal("modal-crew-profile");
}

document.addEventListener("DOMContentLoaded", () => {
  initCommon();
  loadCrew();
  document.getElementById("crew-search").addEventListener("input", filterCrew);
  document.getElementById("filter-rank").addEventListener("change", filterCrew);
  document.getElementById("filter-status").addEventListener("change", filterCrew);
  document.getElementById("add-crew-btn").addEventListener("click", () => openModal("modal-add-crew"));
  document.getElementById("save-crew-btn").addEventListener("click", () => {
    showToast("Crew member added (mock)", "success");
    closeAllModals();
  });
});