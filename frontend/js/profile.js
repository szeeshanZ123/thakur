/**
 * Profile and System Governance Logic for Captain's Treasure Ledger.
 * Displays active user credentials, role permissions matrix, real-time backend health, and role switching.
 */

async function loadProfile() {
  const user = Auth.getUser();
  const role = Auth.getRole();

  // Populate User Info
  const nameEl = document.getElementById("profile-name");
  const handleEl = document.getElementById("profile-handle");
  const roleEl = document.getElementById("profile-role-badge");
  const avatarEl = document.getElementById("profile-avatar");

  if (nameEl) nameEl.textContent = user.name;
  if (handleEl) handleEl.textContent = user.handle || `${user.name.toLowerCase().replace(/\s+/g, '.')}@blackpearl.fleet`;
  if (roleEl) roleEl.innerHTML = `<span class="badge ${role === 'crew' ? 'badge-info' : 'badge-gold'}">${role.toUpperCase()}</span>`;
  if (avatarEl) avatarEl.textContent = user.avatar || "CB";

  renderPermissions(role);
  checkBackendHealth();
}

function renderPermissions(role) {
  const permsContainer = document.getElementById("profile-permissions-list");
  if (!permsContainer) return;

  const permissions = [
    { name: "View Treasury Dashboard & Analytics", captain: true, admin: true, crew: true },
    { name: "Plan Expeditions & Post Revenue", captain: true, admin: true, crew: false },
    { name: "Record Operational Outfitting Expenses", captain: true, admin: true, crew: false },
    { name: "Preview & Finalize Dividend Distributions", captain: true, admin: true, crew: false },
    { name: "Manage Crew Manifest & Ranks", captain: true, admin: true, crew: false },
    { name: "Post Offsetting Ledger Reversals", captain: true, admin: true, crew: false },
    { name: "Export JSON & CSV Voyage Manifests", captain: true, admin: true, crew: true },
    { name: "View Personal Earnings & Payout Slips", captain: true, admin: true, crew: true }
  ];

  permsContainer.innerHTML = permissions.map(p => {
    const isGranted = p[role] || false;
    return `
      <div class="permission-item ${isGranted ? 'perm-allowed' : 'perm-denied'}">
        <span class="perm-icon">${isGranted ? '✓' : '✕'}</span>
        <span class="perm-name">${p.name}</span>
        <span class="perm-status">${isGranted ? 'Authorized' : 'Restricted'}</span>
      </div>
    `;
  }).join("");
}

async function checkBackendHealth() {
  const statusEl = document.getElementById("backend-health-status");
  const latencyEl = document.getElementById("backend-health-latency");
  const urlEl = document.getElementById("backend-api-url");

  if (urlEl) urlEl.textContent = API_BASE_URL;

  const startTime = performance.now();
  try {
    const health = await API.getHealth();
    const duration = Math.round(performance.now() - startTime);

    if (statusEl) {
      statusEl.innerHTML = '<span class="badge badge-green">OPERATIONAL (200 OK)</span>';
    }
    if (latencyEl) {
      latencyEl.textContent = `${duration} ms`;
    }
  } catch (err) {
    if (statusEl) {
      statusEl.innerHTML = '<span class="badge badge-danger">UNREACHABLE</span>';
    }
    if (latencyEl) {
      latencyEl.textContent = 'Timeout / Offline';
    }
  }
}

function selectRolePreset(roleKey) {
  Auth.setRole(roleKey);
  showToast(`Switched active profile to ${roleKey.toUpperCase()}`, "success");
  setTimeout(() => {
    window.location.reload();
  }, 400);
}

function handleLogout() {
  if (confirm("Are you sure you want to end your treasury session and return to dock?")) {
    Auth.clearSession();
    showToast("Logged out successfully.", "info");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 400);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadProfile();
});
