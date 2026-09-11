/**
 * Crew Roster Logic for Captain's Treasure Ledger.
 * Manages pirate crew roster, rank assignments, and individual dividend histories.
 */

let allCrew = [];
let allRanks = [];

async function loadCrew() {
  const container = document.getElementById("crew-table-body");
  showLoading(container, "Loading crew roster...");

  try {
    const [crewList, rankList] = await Promise.all([
      API.getCrew(),
      API.getRanks()
    ]);

    allCrew = crewList || [];
    allRanks = rankList || [];

    renderCrewKPIs(allCrew);
    renderCrewTable(allCrew);
    populateRankDropdowns();
  } catch (err) {
    console.error("Failed to load crew:", err);
    showError(container, "Could not load crew roster from backend.", loadCrew);
  }
}

function renderCrewKPIs(crew) {
  const container = document.getElementById("crew-kpis");
  if (!container) return;

  const total = crew.length;
  const active = crew.filter(c => c.is_active).length;
  const inactive = total - active;

  container.innerHTML = `
    <div class="metric-card"><div class="metric-label">Total Roster</div><div class="metric-value">${total}</div></div>
    <div class="metric-card metric--positive"><div class="metric-label">Active Crew</div><div class="metric-value">${active}</div></div>
    <div class="metric-card metric--warn"><div class="metric-label">Retired / Inactive</div><div class="metric-value">${inactive}</div></div>
    <div class="metric-card metric--gold"><div class="metric-label">Available Ranks</div><div class="metric-value">${allRanks.length}</div></div>`;
}

function renderCrewTable(crew) {
  const tbody = document.getElementById("crew-table-body");
  if (!tbody) return;

  if (!crew.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-row">No crew members found. Click "Add Crew Member" to recruit one.</td></tr>';
    return;
  }

  tbody.innerHTML = crew.map(c => {
    const rank = allRanks.find(r => r.id === c.rank_id);
    const rankTitle = c.rank_name || (rank ? rank.name : "Unassigned");
    const weight = c.share_weight_units || (rank ? rank.share_weight_units : 0);

    return `<tr>
      <td class="td-id">#${String(c.id).padStart(3, "0")}</td>
      <td class="td-name"><strong>${c.name}</strong></td>
      <td>${rankTitle}</td>
      <td class="td-share"><span class="badge badge-gold">${shareWeightToDisplay(weight)}</span></td>
      <td>${getStatusBadge(c.is_active ? "active" : "inactive")}</td>
      <td>${formatDateShort(c.created_at)}</td>
      <td class="td-actions">
        <button class="btn-icon" onclick="viewCrewProfile(${c.id})" title="View Profile & Earnings">${icon('eye', 16)}</button>
        <button class="btn-icon" onclick="openEditCrewModal(${c.id})" title="Edit Crew Member">${icon('document', 16)}</button>
        <button class="btn-icon" onclick="toggleCrewStatus(${c.id})" title="${c.is_active ? 'Deactivate' : 'Activate'}">${icon('lock', 16)}</button>
      </td>
    </tr>`;
  }).join("");
}

function populateRankDropdowns() {
  const filterSel = document.getElementById("filter-rank");
  if (filterSel) {
    filterSel.innerHTML = '<option value="">All Ranks</option>' + allRanks.map(r => `<option value="${r.id}">${r.name} (${shareWeightToDisplay(r.share_weight_units)})</option>`).join("");
  }

  const formSel = document.getElementById("crew-rank");
  if (formSel) {
    formSel.innerHTML = allRanks.map(r => `<option value="${r.id}">${r.name} (${shareWeightToDisplay(r.share_weight_units)})</option>`).join("");
    formSel.addEventListener("change", () => {
      const selected = allRanks.find(r => r.id === parseInt(formSel.value, 10));
      const helper = document.getElementById("crew-share-display");
      if (helper) {
        helper.value = selected ? `${shareWeightToDisplay(selected.share_weight_units)} (${selected.share_weight_units} units)` : "Select rank";
      }
    });
    formSel.dispatchEvent(new Event("change"));
  }
}

function filterCrew() {
  const search = (document.getElementById("crew-search").value || "").toLowerCase().trim();
  const rankId = document.getElementById("filter-rank").value;
  const status = document.getElementById("filter-status").value;

  let filtered = allCrew.filter(c => {
    if (search && !c.name.toLowerCase().includes(search)) return false;
    if (rankId && c.rank_id !== parseInt(rankId, 10)) return false;
    if (status === "active" && !c.is_active) return false;
    if (status === "inactive" && c.is_active) return false;
    return true;
  });

  renderCrewTable(filtered);
}

function openAddCrewModal() {
  document.getElementById("crew-form-title").textContent = "Recruit New Crew Member";
  document.getElementById("crew-id").value = "";
  document.getElementById("crew-name").value = "";
  document.getElementById("crew-active").checked = true;
  if (allRanks.length) {
    document.getElementById("crew-rank").value = allRanks[0].id;
    document.getElementById("crew-rank").dispatchEvent(new Event("change"));
  }
  openModal("crew-modal");
}

function openEditCrewModal(crewId) {
  const c = allCrew.find(x => x.id === crewId);
  if (!c) return;

  document.getElementById("crew-form-title").textContent = `Edit Crew: ${c.name}`;
  document.getElementById("crew-id").value = c.id;
  document.getElementById("crew-name").value = c.name;
  document.getElementById("crew-rank").value = c.rank_id;
  document.getElementById("crew-rank").dispatchEvent(new Event("change"));
  document.getElementById("crew-active").checked = c.is_active;
  openModal("crew-modal");
}

async function saveCrew(e) {
  e.preventDefault();
  const id = document.getElementById("crew-id").value;
  const name = document.getElementById("crew-name").value.trim();
  const rankId = parseInt(document.getElementById("crew-rank").value, 10);
  const isActive = document.getElementById("crew-active").checked;

  if (!name) {
    showToast("Crew member name is required", "error");
    return;
  }

  const payload = {
    name: name,
    rank_id: rankId,
    is_active: isActive
  };

  try {
    if (id) {
      await API.updateCrew(id, payload);
      showToast(`Crew member '${name}' updated!`, "success");
    } else {
      await API.createCrew(payload);
      showToast(`Crew member '${name}' enrolled into the ledger!`, "success");
    }
    closeModal("crew-modal");
    loadCrew();
  } catch (err) {
    showToast(`Failed to save crew: ${err.message}`, "error");
  }
}

async function toggleCrewStatus(crewId) {
  const c = allCrew.find(x => x.id === crewId);
  if (!c) return;

  const action = c.is_active ? "deactivate" : "activate";
  if (!confirm(`Are you sure you want to ${action} ${c.name}?`)) return;

  try {
    if (c.is_active) {
      await API.deactivateCrew(crewId);
      showToast(`${c.name} has been deactivated from active dividend distributions.`, "info");
    } else {
      await API.updateCrew(crewId, { is_active: true });
      showToast(`${c.name} is now active!`, "success");
    }
    loadCrew();
  } catch (err) {
    showToast(`Action failed: ${err.message}`, "error");
  }
}

async function viewCrewProfile(crewId) {
  const c = allCrew.find(m => m.id === crewId);
  if (!c) return;

  openModal("profile-modal");
  const body = document.getElementById("profile-body");
  showLoading(body, "Loading cumulative balance and payout history...");

  try {
    const [balanceRes, payouts] = await Promise.all([
      API.getCrewBalance(crewId).catch(() => ({ running_balance_paise: 0 })),
      API.getCrewPayoutHistory(crewId).catch(() => [])
    ]);

    const rank = allRanks.find(r => r.id === c.rank_id);
    const rankTitle = c.rank_name || (rank ? rank.name : "Unassigned");
    const weight = c.share_weight_units || (rank ? rank.share_weight_units : 0);

    document.getElementById("profile-name").textContent = c.name;
    body.innerHTML = `
      <div class="detail-grid" style="margin-bottom:20px">
        <div class="detail-item"><span class="detail-label">Current Rank</span><span class="detail-value"><strong>${rankTitle}</strong></span></div>
        <div class="detail-item"><span class="detail-label">Share Multiplier</span><span class="detail-value td-share"><span class="badge badge-gold">${shareWeightToDisplay(weight)}</span></span></div>
        <div class="detail-item"><span class="detail-label">Roster Status</span><span class="detail-value">${getStatusBadge(c.is_active ? "active" : "inactive")}</span></div>
      </div>
      
      <div class="kpi-grid" style="margin-bottom:20px">
        <div class="metric-card metric--positive"><div class="metric-label">Cumulative Earnings</div><div class="metric-value">${formatPaise(balanceRes.running_balance_paise || 0)}</div></div>
        <div class="metric-card"><div class="metric-label">Finalized Payouts</div><div class="metric-value">${payouts.length}</div></div>
      </div>

      <h4 class="section-subtitle" style="margin-bottom: 12px;">Chronological Payout History</h4>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Voyage</th>
              <th>Snapshot Share Units</th>
              <th>Dividend Amount</th>
              <th>Status</th>
              <th>Finalized Date</th>
            </tr>
          </thead>
          <tbody>
            ${payouts.length ? payouts.map(p => `
              <tr>
                <td class="td-name">${p.voyage ? p.voyage.name : `Voyage #${p.voyage_id}`}</td>
                <td><code>${p.share_weight_units_used} units</code> (${shareWeightToDisplay(p.share_weight_units_used)})</td>
                <td class="td-amount td-amount-green"><strong>${formatPaise(p.payout_paise)}</strong></td>
                <td>${getStatusBadge(p.status)}</td>
                <td>${formatDate(p.finalized_at || p.calculated_at)}</td>
              </tr>
            `).join("") : '<tr><td colspan="5" class="empty-row">No finalized dividends for this crew member yet.</td></tr>'}
          </tbody>
        </table>
      </div>`;
  } catch (err) {
    showError(body, "Failed to load crew profile details.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadCrew();

  const addBtn = document.getElementById("add-crew-btn");
  if (addBtn) addBtn.addEventListener("click", openAddCrewModal);

  const form = document.getElementById("crew-form");
  if (form) form.addEventListener("submit", saveCrew);

  const searchInput = document.getElementById("crew-search");
  if (searchInput) searchInput.addEventListener("input", filterCrew);

  const filterRank = document.getElementById("filter-rank");
  if (filterRank) filterRank.addEventListener("change", filterCrew);

  const filterStatus = document.getElementById("filter-status");
  if (filterStatus) filterStatus.addEventListener("change", filterCrew);
});