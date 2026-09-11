# Captain's Treasure Ledger — API Data Contract

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

3. **Profit Margins & Percentages:**
   * Margins and percentages are represented in **basis points** ($10000\text{ bps} = 100.00\%$, $2500\text{ bps} = 25.00\%$).

4. **Immutable Transaction Log:**
   * `transaction_logs` is strictly append-only. No `PUT` or `DELETE` endpoints exist.

---

## 2. Standard Error Response Contract

All error responses return a standardized JSON structure with machine-readable error codes:

```json
{
  "detail": "Descriptive human-readable error message"
}
```

### Recognized HTTP Status Codes:
* `400 Bad Request` — Invalid date range (`start_date > end_date`), invalid parameter value.
* `401 Unauthorized` — Missing authentication credentials.
* `403 Forbidden` — Insufficient user permissions for role (`X-User-Role`).
* `404 Not Found` — Requested entity ID does not exist.
* `409 Conflict` — Duplicate revenue posting, double reversal, or modifying finalized state.
* `422 Unprocessable Entity` — Schema validation failure or float/negative financial input.

---

## 3. Analytics & Dashboard Endpoints (`/api/analytics`)

The Analytics API is the authoritative source of truth for the Captain's Treasury Dashboard and Chart.js visualizations.

### A. Dashboard Summary (`GET /api/analytics/dashboard-summary`)
* **Headers**: `X-User-Role: captain`
* **Query Parameters**: `start_date`, `end_date`, `voyage_id`
* **Response Body (`DashboardSummaryResponse`)**:
```json
{
  "total_revenue_paise": 12500000,
  "total_expenses_paise": 4500000,
  "net_profit_paise": 8000000,
  "distributable_profit_paise": 8000000,
  "total_payouts_paise": 8000000,
  "total_voyages": 18,
  "completed_voyages": 15,
  "ongoing_voyages": 2,
  "planned_voyages": 1,
  "active_crew": 24
}
```

---

### B. Revenue Analytics (`GET /api/analytics/revenue`)
* **Query Parameters**: `start_date`, `end_date`
* **Response Body (`RevenueAnalyticsResponse`)**:
```json
{
  "total_revenue_paise": 12500000,
  "average_revenue_paise": 833333,
  "highest_revenue_paise": 3000000,
  "by_voyage": [
    {
      "voyage_id": 1,
      "voyage_name": "Black Pearl Run",
      "revenue_paise": 3000000,
      "date": "2026-09-01T10:00:00Z"
    }
  ]
}
```

---

### C. Expense Analytics (`GET /api/analytics/expenses`)
* **Query Parameters**: `start_date`, `end_date`, `voyage_id`
* **Response Body (`ExpenseAnalyticsResponse`)**:
```json
{
  "total_expenses_paise": 4500000,
  "by_category": [
    {
      "category": "Ship Repair",
      "amount_paise": 2500000,
      "percentage_basis_points": 5555
    },
    {
      "category": "Gunpowder",
      "amount_paise": 2000000,
      "percentage_basis_points": 4444
    }
  ],
  "by_voyage": [
    {
      "voyage_id": 1,
      "voyage_name": "Black Pearl Run",
      "amount_paise": 1200000
    }
  ]
}
```

---

### D. Expense Category Breakdown (`GET /api/analytics/expenses/by-category`)
* **Query Parameters**: `start_date`, `end_date`, `voyage_id`
* **Response Body (`ExpenseBreakdownResponse`)**:
```json
{
  "items": [
    {
      "category": "Ship Repair",
      "amount_paise": 2500000,
      "percentage_basis_points": 5555
    }
  ]
}
```

---

### E. Profit Analytics (`GET /api/analytics/profit`)
* **Query Parameters**: `start_date`, `end_date`
* **Response Body (`ProfitAnalyticsResponse`)**:
```json
{
  "total_revenue_paise": 12500000,
  "total_expenses_paise": 4500000,
  "net_profit_paise": 8000000,
  "distributable_profit_paise": 8000000,
  "profitable_voyages": 12,
  "loss_making_voyages": 2,
  "break_even_voyages": 1,
  "average_profit_margin_basis_points": 6400
}
```

---

### F. Voyage Profitability & ROI (`GET /api/analytics/voyages/profitability`)
* **Query Parameters**: `start_date`, `end_date`, `sort_by`, `order`, `page`, `page_size`
* **Response Body (`PaginatedResponse[VoyageProfitabilityItem]`)**:
```json
{
  "items": [
    {
      "voyage_id": 1,
      "voyage_name": "Black Pearl Run",
      "date": "2026-09-01T10:00:00Z",
      "revenue_paise": 3000000,
      "expenses_paise": 1000000,
      "net_profit_paise": 2000000,
      "status": "PROFITABLE",
      "roi_basis_points": 20000
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### G. Top & Loss Voyages
* `GET /api/analytics/voyages/top?limit=5` — Ranked by `net_profit_paise DESC`.
* `GET /api/analytics/voyages/losses` — Ranked by `net_profit_paise ASC` (largest losses first).

---

### H. Crew Earnings Leaderboard (`GET /api/analytics/crew/earnings`)
* **Query Parameters**: `page`, `page_size`, `sort_by`, `order`
* **Response Body (`PaginatedResponse[CrewEarningsItem]`)**:
```json
{
  "items": [
    {
      "crew_member_id": 1,
      "name": "Jack Sparrow",
      "rank": "Captain",
      "total_earnings_paise": 5000000,
      "payout_count": 8
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### I. Rank Payout Analytics (`GET /api/analytics/ranks/payouts`)
* **Response Body (`RankPayoutsResponse`)**:
```json
{
  "ranks": [
    {
      "rank_id": 1,
      "rank": "Captain",
      "share_weight_units": 200,
      "crew_count": 1,
      "total_payout_paise": 5000000,
      "payout_count": 8
    }
  ]
}
```

---

### J. Time Series (`GET /api/analytics/time-series`)
* **Query Parameters**: `group_by` (`daily`, `weekly`, `monthly`), `start_date`, `end_date`
* **Response Body (`TimeSeriesResponse`)**:
```json
{
  "group_by": "monthly",
  "data": [
    {
      "period": "2026-09",
      "revenue_paise": 12500000,
      "expenses_paise": 4500000,
      "net_profit_paise": 8000000
    }
  ]
}
```

---

### K. Payout Analytics (`GET /api/analytics/payouts`)
* **Query Parameters**: `start_date`, `end_date`, `voyage_id`
* **Response Body (`PayoutAnalyticsResponse`)**:
```json
{
  "total_payouts_paise": 8000000,
  "payout_count": 24,
  "average_payout_paise": 333333,
  "by_voyage": [
    {
      "voyage_id": 1,
      "voyage_name": "Black Pearl Run",
      "total_payout_paise": 8000000,
      "crew_count": 24
    }
  ],
  "by_rank": [
    {
      "rank": "Captain",
      "total_payout_paise": 2000000,
      "payout_count": 1
    }
  ]
}
```

---

## 4. Voyage Manifest Exports (`/api/voyages/{voyage_id}/export`)

The Export API provides downloadable, verifiable financial manifests in JSON and CSV formats for external auditing and spreadsheet analysis.

### A. JSON Manifest (`GET /api/voyages/{voyage_id}/export/json`)
* **Headers**: `X-User-Role: captain`
* **Response Content-Type**: `application/json`
* **Response Header**: `Content-Disposition: attachment; filename="voyage_{voyage_id}_manifest.json"`
* **Response Payload Example**:
```json
{
  "manifest_version": "1.0",
  "exported_at": "2026-09-11T12:00:00Z",
  "export_format": "json",
  "voyage": {
    "id": 1,
    "name": "Black Pearl Run",
    "date": "2026-09-01T10:00:00Z",
    "description": "Expedition to Isla de Muerta",
    "status": "completed",
    "created_at": "2026-09-01T08:00:00Z"
  },
  "financial_summary": {
    "revenue_paise": 10000000,
    "expenses_paise": 3000000,
    "net_profit_paise": 7000000,
    "distributable_profit_paise": 7000000
  },
  "payout_status": "FINALIZED",
  "crew": [
    {
      "crew_member_id": 1,
      "name": "Jack Sparrow",
      "rank": "Captain",
      "current_share_weight_units": 200,
      "is_active": true
    }
  ],
  "expenses": [
    {
      "expense_id": 10,
      "category": "Ship Repair",
      "amount_paise": 3000000,
      "date": "2026-09-02T14:00:00Z",
      "description": "Hull reinforcement",
      "created_at": "2026-09-02T14:05:00Z"
    }
  ],
  "payouts": [
    {
      "payout_id": 101,
      "crew_member_id": 1,
      "crew_member_name": "Jack Sparrow",
      "rank": "Captain",
      "share_weight_units_used": 200,
      "payout_paise": 7000000,
      "status": "finalized",
      "calculated_at": "2026-09-05T18:00:00Z",
      "finalized_at": "2026-09-05T18:00:00Z"
    }
  ],
  "transactions": [
    {
      "transaction_id": 501,
      "transaction_type": "CREDIT",
      "amount_paise": 10000000,
      "description": "Voyage loot credited",
      "reference_type": "voyage_revenue",
      "reference_id": 1,
      "timestamp": "2026-09-01T10:00:00Z",
      "created_at": "2026-09-01T10:00:00Z"
    }
  ]
}
```

---

### B. CSV Manifest (`GET /api/voyages/{voyage_id}/export/csv`)
* **Headers**: `X-User-Role: captain`
* **Response Content-Type**: `text/csv`
* **Response Header**: `Content-Disposition: attachment; filename="voyage_{voyage_id}_manifest.csv"`
* **CSV Columns**:
  `record_type,id,voyage_id,name,category_or_rank,amount_paise,share_weight_units,date_or_timestamp,description_or_status,reference_type,reference_id`
* **Spreadsheet Protection**: Cells starting with `=`, `+`, `-`, or `@` are safely escaped with a leading single quote `'`.
