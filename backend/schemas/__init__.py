"""
Pydantic schemas package for Captain's Treasure Ledger API.
Exports all request validation, response serialization, and analytics data contracts.
"""

from backend.schemas.rank import (
    RankBase,
    RankCreate,
    RankUpdate,
    RankResponse,
)
from backend.schemas.crew import (
    CrewBase,
    CrewCreate,
    CrewUpdate,
    CrewResponse,
    CrewSummary,
    CrewLedgerEntry,
)
from backend.schemas.voyage import (
    VoyageBase,
    VoyageCreate,
    VoyageUpdate,
    VoyageResponse,
    VoyageSummary,
    VoyageFinancialSummaryResponse,
    RevenuePostRequest,
)
from backend.schemas.expense import (
    ExpenseBase,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
)
from backend.schemas.transaction import (
    TransactionResponse,
    TransactionCreateInternal,
    TransactionReversalRequest,
    TransactionCorrectionRequest,
)
from backend.schemas.payout import (
    PayoutResponse,
    PayoutPreviewItem,
    PayoutPreview,
    PayoutFinalizeResponse,
)
from backend.schemas.analytics import (
    DashboardKPIs,
    RevenueExpensePoint,
    RevenueExpenseResponse,
    ExpenseBreakdownItem,
    ExpenseBreakdownResponse,
    ProfitAnalyticsResponse,
    CrewEarningsItem,
    CrewEarningsResponse,
    PaginationParams,
    PaginatedResponse,
)

__all__ = [
    # Rank schemas
    "RankBase",
    "RankCreate",
    "RankUpdate",
    "RankResponse",
    # Crew schemas
    "CrewBase",
    "CrewCreate",
    "CrewUpdate",
    "CrewResponse",
    "CrewSummary",
    "CrewLedgerEntry",
    # Voyage schemas
    "VoyageBase",
    "VoyageCreate",
    "VoyageUpdate",
    "VoyageResponse",
    "VoyageSummary",
    "VoyageFinancialSummaryResponse",
    "RevenuePostRequest",
    # Expense schemas
    "ExpenseBase",
    "ExpenseCreate",
    "ExpenseUpdate",
    "ExpenseResponse",
    # Transaction schemas
    "TransactionResponse",
    "TransactionCreateInternal",
    "TransactionReversalRequest",
    "TransactionCorrectionRequest",
    # Payout schemas
    "PayoutResponse",
    "PayoutPreviewItem",
    "PayoutPreview",
    "PayoutFinalizeResponse",
    # Analytics schemas
    "DashboardKPIs",
    "RevenueExpensePoint",
    "RevenueExpenseResponse",
    "ExpenseBreakdownItem",
    "ExpenseBreakdownResponse",
    "ProfitAnalyticsResponse",
    "CrewEarningsItem",
    "CrewEarningsResponse",
    "PaginationParams",
    "PaginatedResponse",
]

