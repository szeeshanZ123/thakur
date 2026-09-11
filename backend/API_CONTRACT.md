# Captain's Treasure Ledger — API Data Contract (Phase 3)

This document establishes the official REST API specification between the **FastAPI Backend** and the **HTML/CSS/JavaScript + Chart.js Frontend**.

---

## 1. Core Financial Standard

1. **Monetary Values (Paise):**
   * All monetary amounts are canonical **integers in Indian paise** ($₹1.00 = 100\text{ paise}$).
   * Example: Gross Loot of $₹50,000.75$ is passed as `5000075`.
   * **Rule:** The frontend formats paise into rupees for visual presentation ($\frac{\text{paise}}{100}$); all calculations remain on the backend.

2. **Share Weight Units:**
   * Rank shares are canonical **integers** where $100\text{ units} = 1.0\times\text{ share}$.
   * Example: Captain ($2.0\times$) is `200` units; Powder Monkey ($0.5\times$) is `50` units.

3. **Profit Margins:**
   * Margins are represented in **basis points** ($10000\text{ bps} = 100.00\%$, $2500\text{ bps} = 25.00\%$).

4. **Immutable Transaction Log:**
   * `transaction_logs` is strictly append-only. No `PUT` or `DELETE` endpoints exist.

---

## 2. Standard Error Response Contract

All error responses return a standardized JSON structure with machine-readable error codes:

```json
{
  "detail": "Descriptive human-readable error message",
  "code": "VALIDATION_ERROR"
}
```

### Recognized Error Codes:
* `VALIDATION_ERROR` — Invalid schema payload or non-integer financial input.
* `NOT_FOUND` — Requested entity ID does not exist.
* `DUPLICATE_RECORD` — Unique constraint violation (e.g. duplicate rank title).
* `INVALID_STATUS` — Action rejected due to current lifecycle status.
* `PAYOUT_ALREADY_FINALIZED` — Attempted to alter a finalized dividend distribution.
* `NO_ACTIVE_CREW` — No active crew members available for dividend division.
* `IMMUTABLE_TRANSACTION` — Modification to committed audit logs was rejected.

---

## 3. Endpoints Specification (Phase 4 Planned)

### A. Ranks (`/api/ranks`)

| Method | Endpoint | Description | Request Body | Response Body |
|---|---|---|---|---|
| `GET` | `/api/ranks` | List all pirate ranks | *None* | `List[RankResponse]` |
| `POST` | `/api/ranks` | Create new rank | `RankCreate` | `RankResponse` (201) |
| `PUT` | `/api/ranks/{id}` | Update rank title / shares | `RankUpdate` | `RankResponse` |
| `DELETE` | `/api/ranks/{id}` | Delete rank (fails if assigned) | *None* | `{"success": true}` |

---

### B. Crew Members (`/api/crew`)

| Method | Endpoint | Description | Query / Body | Response Body |
|---|---|---|---|---|
| `GET` | `/api/crew` | List crew members | `?is_active=true&rank_id=1` | `List[CrewResponse]` |
| `POST` | `/api/crew` | Register crew member | `CrewCreate` | `CrewResponse` (201) |
| `GET` | `/api/crew/{id}` | Get crew details | *None* | `CrewResponse` |
| `PUT` | `/api/crew/{id}` | Update details / toggle active | `CrewUpdate` | `CrewResponse` |
| `GET` | `/api/crew/{id}/ledger` | View pirate dividend history | *None* | `List[CrewLedgerEntry]` |

---

### C. Voyages (`/api/voyages`)

| Method | Endpoint | Description | Query / Body | Response Body |
|---|---|---|---|---|
| `GET` | `/api/voyages` | List voyages with metrics | `?status=completed` | `List[VoyageResponse]` |
| `POST` | `/api/voyages` | Log a new voyage | `VoyageCreate` | `VoyageResponse` (201) |
| `GET` | `/api/voyages/{id}` | Get voyage summary | *None* | `VoyageResponse` |
| `PUT` | `/api/voyages/{id}` | Update revenue / status | `VoyageUpdate` | `VoyageResponse` |

---

### D. Expenses (`/api/expenses`)

| Method | Endpoint | Description | Query / Body | Response Body |
|---|---|---|---|---|
| `GET` | `/api/expenses` | List expenses | `?voyage_id=1&category=Ship+Repair` | `List[ExpenseResponse]` |
| `POST` | `/api/expenses` | Record operational expense | `ExpenseCreate` | `ExpenseResponse` (201) |
| `GET` | `/api/expenses/{id}` | Get expense entry | *None* | `ExpenseResponse` |

---

### E. Transaction Log (`/api/transactions`)

| Method | Endpoint | Description | Query / Body | Response Body |
|---|---|---|---|---|
| `GET` | `/api/transactions` | Full chronological audit log | `?transaction_type=CREDIT` | `List[TransactionResponse]` |
| `GET` | `/api/voyages/{id}/transactions` | Transactions for specific voyage | *None* | `List[TransactionResponse]` |

*(Note: No PUT/DELETE endpoints exist for transaction logs).*

---

### F. Payouts & Dividend Division (`/api/payouts`)

| Method | Endpoint | Description | Request Body | Response Body |
|---|---|---|---|---|
| `POST` | `/api/voyages/{id}/calculate-payouts` | Dry-run dividend calculation preview | *None* | `PayoutPreview` |
| `POST` | `/api/voyages/{id}/finalize-payouts` | Commit immutable payout records | *None* | `PayoutFinalizeResponse` |
| `GET` | `/api/voyages/{id}/payouts` | Retrieve voyage payout distributions | *None* | `List[PayoutResponse]` |

---

### G. Dashboard & Visual Analytics (for Chart.js)

| Method | Endpoint | Description | Response Body |
|---|---|---|---|
| `GET` | `/api/dashboard/kpis` | Summary cards (Total loot, expenses, profit, active crew) | `DashboardKPIs` |
| `GET` | `/api/analytics/revenue-vs-expenses` | Time-series bar/line chart datasets | `RevenueExpenseResponse` |
| `GET` | `/api/analytics/expense-breakdown` | Category doughnut/pie chart datasets | `ExpenseBreakdownResponse` |
| `GET` | `/api/analytics/profit` | Aggregate profit and margin analytics | `ProfitAnalyticsResponse` |
| `GET` | `/api/analytics/crew-earnings` | Top-earning crew rankings | `CrewEarningsResponse` |
