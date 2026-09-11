/**
 * Authentication and Role State Management for Captain's Treasure Ledger.
 * Provides client-side role synchronization and permission validation.
 */

const AUTH_ROLES = {
  CAPTAIN: {
    id: "captain",
    title: "Captain",
    subtitle: "Fleet Commander",
    name: "Edward 'Blackbeard' Teach",
    avatar: "EB",
    badgeClass: "badge-gold",
    permissions: ["manage_voyages", "post_revenue", "manage_expenses", "preview_payouts", "finalize_payouts", "view_ledger", "view_analytics", "export"]
  },
  ADMIN: {
    id: "admin",
    title: "Administrator / Quartermaster",
    subtitle: "Treasury Master",
    name: "Anne Bonny",
    avatar: "AB",
    badgeClass: "badge-active",
    permissions: ["manage_ranks", "manage_crew", "manage_voyages", "post_revenue", "manage_expenses", "preview_payouts", "finalize_payouts", "reverse_transactions", "view_ledger", "view_analytics", "export"]
  },
  CREW: {
    id: "crew",
    title: "Crew Member",
    subtitle: "Deck Officer",
    name: "Israel Hands",
    avatar: "IH",
    badgeClass: "badge-info",
    permissions: ["view_profile", "view_earnings", "view_voyages", "export"]
  }
};

class AuthManager {
  constructor() {
    this.storageKey = "treasure_user_role";
    this.userKey = "treasure_user_info";
  }

  getCurrentRole() {
    return localStorage.getItem(this.storageKey) || "captain";
  }

  getUserInfo() {
    const roleId = this.getCurrentRole();
    return AUTH_ROLES[roleId.toUpperCase()] || AUTH_ROLES.CAPTAIN;
  }

  setRole(roleId) {
    const cleanRole = (roleId || "captain").toLowerCase();
    localStorage.setItem(this.storageKey, cleanRole);
    if (typeof API !== "undefined" && API.setRole) {
      API.setRole(cleanRole);
    }
    this.updateUI();
  }

  login(roleId = "captain") {
    this.setRole(roleId);
    window.location.href = "dashboard.html";
  }

  logout() {
    localStorage.removeItem(this.storageKey);
    localStorage.removeItem(this.userKey);
    window.location.href = "login.html";
  }

  hasPermission(permission) {
    const user = this.getUserInfo();
    return user.permissions.includes(permission);
  }

  updateUI() {
    const user = this.getUserInfo();

    // Update Captain Card in sidebar if present
    const cardName = document.querySelector(".captain-name");
    const cardRole = document.querySelector(".captain-role");
    const cardAvatar = document.querySelector(".avatar");

    if (cardName) cardName.textContent = user.name;
    if (cardRole) cardRole.textContent = user.title;
    if (cardAvatar) cardAvatar.textContent = user.avatar;

    // Update Role Switcher / Badges if present
    document.querySelectorAll("[data-current-role]").forEach(el => {
      el.textContent = user.title;
    });

    // Hide/Show elements based on role permission
    document.querySelectorAll("[data-require-role]").forEach(el => {
      const allowedRoles = (el.getAttribute("data-require-role") || "").toLowerCase().split(",");
      if (allowedRoles.includes(user.id)) {
        el.style.display = "";
      } else {
        el.style.display = "none";
      }
    });

    document.querySelectorAll("[data-require-perm]").forEach(el => {
      const perm = el.getAttribute("data-require-perm");
      if (this.hasPermission(perm)) {
        el.style.display = "";
      } else {
        el.style.display = "none";
      }
    });
  }
}

const Auth = new AuthManager();

// Automatically update UI on load
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    Auth.updateUI();
  });
}
