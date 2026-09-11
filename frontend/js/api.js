/**
 * Central API Client for Captain's Treasure Ledger.
 * Directly integrates with the FastAPI Backend (http://127.0.0.1:8000).
 * 
 * CRITICAL FINANCIAL RULES:
 * - Backend is the single source of truth for all financial math.
 * - All monetary amounts are communicated as exact INTEGER PAISE.
 * - All share weights are communicated as exact INTEGER UNITS (100 = 1.0x).
 * - Frontend performs zero float calculations for financial records.
 */

const API_CONFIG = {
  BASE_URL: (window.location.port === "3000" || window.location.port === "5500") 
    ? "http://127.0.0.1:8000" 
    : window.location.origin
};

class ApiClient {
  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
  }

  getRole() {
    return localStorage.getItem("treasure_user_role") || "captain";
  }

  setRole(role) {
    localStorage.setItem("treasure_user_role", role.toLowerCase());
  }

  getHeaders() {
    return {
      "Content-Type": "application/json",
      "X-User-Role": this.getRole()
    };
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, config);

      if (response.status === 401) {
        showToast("Your session has expired. Please log in.", "error");
        setTimeout(() => { window.location.href = "login.html"; }, 1000);
        throw new Error("Unauthorized");
      }

      const isJson = (response.headers.get("content-type") || "").includes("application/json");
      const data = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        const errorDetail = (data && data.detail) ? data.detail : (typeof data === "string" ? data : "Request failed");
        throw new Error(errorDetail);
      }

      return data;
    } catch (err) {
      console.error(`API Error [${options.method || 'GET'} ${endpoint}]:`, err);
      throw err;
    }
  }

  // --- Health & Info ---
  async health() {
    return this.request("/health");
  }

  // --- Ranks API ---
  async getRanks(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await this.request(`/api/ranks${query ? '?' + query : ''}`);
    return Array.isArray(res) ? res : (res.items || res.ranks || []);
  }

  async getRankById(id) {
    return this.request(`/api/ranks/${id}`);
  }

  async createRank(data) {
    return this.request("/api/ranks", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async updateRank(id, data) {
    return this.request(`/api/ranks/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  }

  async deleteRank(id) {
    return this.request(`/api/ranks/${id}`, {
      method: "DELETE"
    });
  }

  // --- Crew API ---
  async getCrew(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await this.request(`/api/crew${query ? '?' + query : ''}`);
    return Array.isArray(res) ? res : (res.items || res.crew || []);
  }

  async getCrewById(id) {
    return this.request(`/api/crew/${id}`);
  }

  async createCrew(data) {
    return this.request("/api/crew", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async updateCrew(id, data) {
    return this.request(`/api/crew/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  }

  async deactivateCrew(id) {
    return this.request(`/api/crew/${id}`, {
      method: "DELETE"
    });
  }

  async getCrewLedger(id) {
    return this.request(`/api/crew/${id}/ledger`);
  }

  async getCrewBalance(id) {
    return this.request(`/api/crew/${id}/balance`);
  }

  // --- Voyages API ---
  async getVoyages(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await this.request(`/api/voyages${query ? '?' + query : ''}`);
    return Array.isArray(res) ? res : (res.items || res.voyages || []);
  }

  async getVoyageById(id) {
    return this.request(`/api/voyages/${id}`);
  }

  async createVoyage(data) {
    return this.request("/api/voyages", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async updateVoyage(id, data) {
    return this.request(`/api/voyages/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  }

  async cancelVoyage(id) {
    return this.request(`/api/voyages/${id}`, {
      method: "DELETE"
    });
  }

  async getVoyageSummary(id) {
    return this.request(`/api/voyages/${id}/summary`);
  }

  async postVoyageRevenue(id, revenue_paise, description = "") {
    return this.request(`/api/voyages/${id}/revenue`, {
      method: "POST",
      body: JSON.stringify({ revenue_paise, description })
    });
  }

  // --- Expenses API ---
  async getExpenses(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await this.request(`/api/expenses${query ? '?' + query : ''}`);
    return Array.isArray(res) ? res : (res.items || res.expenses || []);
  }

  async getExpenseById(id) {
    return this.request(`/api/expenses/${id}`);
  }

  async createExpense(data) {
    return this.request("/api/expenses", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  // --- Transactions API ---
  async getTransactions(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await this.request(`/api/transactions${query ? '?' + query : ''}`);
    return Array.isArray(res) ? res : (res.items || res.transactions || []);
  }

  async getTransactionById(id) {
    return this.request(`/api/transactions/${id}`);
  }

  async reverseTransaction(id, reason) {
    return this.request(`/api/transactions/${id}/reverse`, {
      method: "POST",
      body: JSON.stringify({ reason })
    });
  }

  async correctTransaction(id, new_amount_paise, reason) {
    return this.request(`/api/transactions/${id}/correct`, {
      method: "POST",
      body: JSON.stringify({ new_amount_paise, reason })
    });
  }

  // --- Payouts & Dividends API ---
  async getPayouts(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await this.request(`/api/payouts${query ? '?' + query : ''}`);
    return Array.isArray(res) ? res : (res.items || res.payouts || []);
  }

  async previewVoyagePayouts(voyageId) {
    return this.request(`/api/payouts/voyages/${voyageId}/preview`);
  }

  async finalizeVoyagePayouts(voyageId) {
    return this.request(`/api/payouts/voyages/${voyageId}/finalize`, {
      method: "POST"
    });
  }

  async getCrewPayoutHistory(crewId) {
    return this.request(`/api/payouts/crew/${crewId}/history`);
  }

  async getCrewPayoutBalance(crewId) {
    return this.request(`/api/payouts/crew/${crewId}/balance`);
  }

  // --- Analytics API ---
  async getDashboardSummary(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/analytics/dashboard${query ? '?' + query : ''}`);
  }

  async getAnalyticsDashboard(params = {}) {
    return this.getDashboardSummary(params);
  }

  async getAnalytics(params = {}) {
    return this.getDashboardSummary(params);
  }

  async getRevenueAnalytics(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/analytics/revenue${query ? '?' + query : ''}`);
  }

  async getExpenseAnalytics(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/analytics/expenses${query ? '?' + query : ''}`);
  }

  async getProfitAnalytics(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/analytics/profit${query ? '?' + query : ''}`);
  }

  async getExpenseCategories(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/analytics/expenses/categories${query ? '?' + query : ''}`);
  }

  async getVoyagesProfitability(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/analytics/voyages/profitability${query ? '?' + query : ''}`);
  }

  async getTopVoyages(limit = 5) {
    return this.request(`/api/analytics/voyages/top?limit=${limit}`);
  }

  async getLossMakingVoyages(limit = 5) {
    return this.request(`/api/analytics/voyages/loss-making?limit=${limit}`);
  }

  async getCrewEarnings(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/analytics/crew/earnings${query ? '?' + query : ''}`);
  }

  async getRankPayouts() {
    return this.request("/api/analytics/ranks/payouts");
  }

  async getTimeSeries(interval = "month") {
    return this.request(`/api/analytics/timeseries?interval=${interval}`);
  }

  // --- Exports API ---
  getExportUrl(voyageId, format = "json") {
    const ext = format.toLowerCase() === "csv" ? "csv" : "json";
    return `${this.baseUrl}/api/voyages/${voyageId}/export/${ext}`;
  }

  async downloadExport(voyageId, format = "json") {
    const url = this.getExportUrl(voyageId, format);
    const filename = `voyage_${voyageId}_manifest.${format.toLowerCase()}`;

    try {
      const res = await fetch(url, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`Export failed with HTTP ${res.status}`);
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      showToast(`Manifest downloaded as ${format.toUpperCase()}`, "success");
    } catch (err) {
      console.error("Export download failed:", err);
      showToast(`Export failed: ${err.message}`, "error");
    }
  }
}

// Global API Singleton
const API = new ApiClient();
