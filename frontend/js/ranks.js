/**
 * Rank Management Logic for Captain's Treasure Ledger.
 * Configures pirate rank hierarchy and exact integer share weight units (100 = 1.0x).
 */

let allRanks = [];

async function loadRanks() {
  const container = document.getElementById("ranks-table-body");
  showLoading(container, "Loading rank hierarchy...");

  try {
    allRanks = await API.getRanks();
    renderRanksKPIs(allRanks);
    renderRanksTable(allRanks);
  } catch (err) {
    console.error("Failed to load ranks:", err);
    showError(container, "Could not load ranks from backend.", loadRanks);
  }
}

function renderRanksKPIs(ranks) {
  const container = document.getElementById("ranks-kpis");
  if (!container) return;

  const total = ranks.length;
  const active = ranks.filter(r => r.is_active).length;
  const highest = ranks.reduce((max, r) => r.share_weight_units > max.share_weight_units ? r : max, { name: "N/A", share_weight_units: 0 });

  container.innerHTML = `
    <div class="metric-card"><div class="metric-label">Configured Ranks</div><div class="metric-value">${total}</div></div>
    <div class="metric-card metric--positive"><div class="metric-label">Active Ranks</div><div class="metric-value">${active}</div></div>
    <div class="metric-card metric--gold"><div class="metric-label">Highest Share Weight</div><div class="metric-value metric-value-sm">${highest.name}<br><span class="metric-sub">${shareWeightToDisplay(highest.share_weight_units)} (${highest.share_weight_units} units)</span></div></div>`;
}

function renderRanksTable(ranks) {
  const tbody = document.getElementById("ranks-table-body");
  if (!tbody) return;

  if (!ranks.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No ranks found. Click "Add Rank" to create one.</td></tr>';
    return;
  }

  tbody.innerHTML = ranks.map(r => `
    <tr>
      <td class="td-id">#${String(r.id).padStart(2, "0")}</td>
      <td class="td-name"><strong>${r.name}</strong></td>
      <td class="td-share"><span class="badge badge-gold">${shareWeightToDisplay(r.share_weight_units)}</span></td>
      <td><code>${r.share_weight_units} units</code></td>
      <td>${getStatusBadge(r.is_active ? "active" : "inactive")}</td>
      <td class="td-actions">
        <button class="btn btn-secondary btn-sm" onclick="openEditRankModal(${r.id})">Edit</button>
        <button class="btn btn-secondary btn-sm" onclick="deleteRank(${r.id})">${r.is_active ? "Deactivate" : "Activate"}</button>
      </td>
    </tr>
  `).join("");
}

function openAddRankModal() {
  document.getElementById("rank-form-title").textContent = "Add New Pirate Rank";
  document.getElementById("rank-id").value = "";
  document.getElementById("rank-name").value = "";
  document.getElementById("rank-units").value = "100";
  document.getElementById("rank-active").checked = true;
  updateRankShareHelper();
  openModal("rank-modal");
}

function openEditRankModal(rankId) {
  const r = allRanks.find(x => x.id === rankId);
  if (!r) return;

  document.getElementById("rank-form-title").textContent = `Edit Rank: ${r.name}`;
  document.getElementById("rank-id").value = r.id;
  document.getElementById("rank-name").value = r.name;
  document.getElementById("rank-units").value = r.share_weight_units;
  document.getElementById("rank-active").checked = r.is_active;
  updateRankShareHelper();
  openModal("rank-modal");
}

function updateRankShareHelper() {
  const units = parseInt(document.getElementById("rank-units").value, 10) || 0;
  const helper = document.getElementById("rank-share-helper");
  if (helper) {
    helper.textContent = `${units} units = ${(units / 100).toFixed(2)}x dividend share multiplier`;
  }
}

async function saveRank(e) {
  e.preventDefault();
  const id = document.getElementById("rank-id").value;
  const name = document.getElementById("rank-name").value.trim();
  const units = parseInt(document.getElementById("rank-units").value, 10);
  const isActive = document.getElementById("rank-active").checked;

  if (!name) {
    showToast("Rank name is required", "error");
    return;
  }
  if (!units || units <= 0) {
    showToast("Share weight units must be greater than zero", "error");
    return;
  }

  const payload = {
    name: name,
    share_weight_units: units,
    is_active: isActive
  };

  try {
    if (id) {
      await API.updateRank(id, payload);
      showToast(`Rank '${name}' updated successfully!`, "success");
    } else {
      await API.createRank(payload);
      showToast(`Rank '${name}' created successfully!`, "success");
    }
    closeModal("rank-modal");
    loadRanks();
  } catch (err) {
    showToast(`Failed to save rank: ${err.message}`, "error");
  }
}

async function deleteRank(id) {
  const r = allRanks.find(x => x.id === id);
  if (!r) return;

  if (!confirm(`Are you sure you want to change the status of rank '${r.name}'?`)) return;

  try {
    await API.updateRank(id, { is_active: !r.is_active });
    showToast(`Rank '${r.name}' updated!`, "success");
    loadRanks();
  } catch (err) {
    showToast(`Failed to update rank: ${err.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadRanks();

  const addBtn = document.getElementById("add-rank-btn");
  if (addBtn) addBtn.addEventListener("click", openAddRankModal);

  const form = document.getElementById("rank-form");
  if (form) form.addEventListener("submit", saveRank);

  const unitsInput = document.getElementById("rank-units");
  if (unitsInput) unitsInput.addEventListener("input", updateRankShareHelper);
});
