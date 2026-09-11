"""
Pydantic schemas package for Captain's Treasure Ledger API.
Exports all request validation, response serialization, analytics, and manifest export data contracts.
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
    CrewBalanceResponse,
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
    DashboardSummaryResponse,
    RevenueByVoyageItem,
    RevenueAnalyticsResponse,
    ExpenseCategoryItem,
    ExpenseByVoyageItem,
    ExpenseAnalyticsResponse,
    ExpenseBreakdownItem,
    ExpenseBreakdownResponse,
    ProfitAnalyticsResponse,
    VoyageProfitabilityItem,
    VoyageProfitabilityResponse,
    TopVoyageItem,
    TopVoyagesResponse,
    LossVoyagesResponse,
    CrewEarningsItem,
    CrewEarningsResponse,
    RankPayoutItem,
    RankPayoutsResponse,
    TimeSeriesPoint,
    TimeSeriesResponse,
    PayoutVoyageSummary,
    PayoutRankSummary,
    PayoutAnalyticsResponse,
    RevenueExpensePoint,
    RevenueExpenseResponse,
    PaginationParams,
    PaginatedResponse,
)
from backend.schemas.export import (
    VoyageManifestMetadata,
    VoyageManifestInfo,
    VoyageManifestFinancialSummary,
    VoyageManifestCrewItem,
    VoyageManifestExpenseItem,
    VoyageManifestPayoutItem,
    VoyageManifestTransactionItem,
    VoyageManifestResponse,
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
    "CrewBalanceResponse",
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
    "DashboardSummaryResponse",
    "RevenueByVoyageItem",
    "RevenueAnalyticsResponse",
    "ExpenseCategoryItem",
    "ExpenseByVoyageItem",
    "ExpenseAnalyticsResponse",
    "ExpenseBreakdownItem",
    "ExpenseBreakdownResponse",
    "ProfitAnalyticsResponse",
    "VoyageProfitabilityItem",
    "VoyageProfitabilityResponse",
    "TopVoyageItem",
    "TopVoyagesResponse",
    "LossVoyagesResponse",
    "CrewEarningsItem",
    "CrewEarningsResponse",
    "RankPayoutItem",
    "RankPayoutsResponse",
    "TimeSeriesPoint",
    "TimeSeriesResponse",
    "PayoutVoyageSummary",
    "PayoutRankSummary",
    "PayoutAnalyticsResponse",
    "RevenueExpensePoint",
    "RevenueExpenseResponse",
    "PaginationParams",
    "PaginatedResponse",
    # Export schemas
    "VoyageManifestMetadata",
    "VoyageManifestInfo",
    "VoyageManifestFinancialSummary",
    "VoyageManifestCrewItem",
    "VoyageManifestExpenseItem",
    "VoyageManifestPayoutItem",
    "VoyageManifestTransactionItem",
    "VoyageManifestResponse",
]
