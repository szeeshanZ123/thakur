"""
Pydantic schemas for Treasury Dashboard KPIs, Chart.js visual contracts, and financial analytics.
Strict integer paise typing for all currency values and basis points for percentages.
"""

from typing import List, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar("T")


class DashboardKPIs(BaseModel):
    """Aggregated financial snapshot for the Captain's Dashboard KPI cards (legacy & consolidated)."""
    total_revenue_paise: int = Field(..., description="Cumulative gross revenue across all voyages in integer paise")
    total_expenses_paise: int = Field(..., description="Cumulative operational expenses in integer paise")
    net_profit_paise: int = Field(..., description="Total treasury net profit in integer paise")
    total_distributed_paise: int = Field(..., description="Total dividends distributed to crew in integer paise")
    active_crew_count: int = Field(..., description="Number of active crew members aboard")
    completed_voyage_count: int = Field(..., description="Number of completed expeditions")


class DashboardSummaryResponse(BaseModel):
    """Comprehensive dashboard KPI summary response."""
    total_revenue_paise: int = Field(..., description="Total effective gross revenue in integer paise")
    total_expenses_paise: int = Field(..., description="Total effective operational expenses in integer paise")
    net_profit_paise: int = Field(..., description="Total net profit (can be negative during loss) in integer paise")
    distributable_profit_paise: int = Field(..., description="Total distributable profit (clamped to 0) in integer paise")
    total_payouts_paise: int = Field(..., description="Total finalized dividends paid to crew in integer paise")
    total_voyages: int = Field(..., description="Total count of all voyages")
    completed_voyages: int = Field(..., description="Count of completed voyages")
    ongoing_voyages: int = Field(..., description="Count of ongoing voyages")
    planned_voyages: int = Field(..., description="Count of planned voyages")
    active_crew: int = Field(..., description="Count of currently active crew members")


class RevenueByVoyageItem(BaseModel):
    """Voyage revenue breakdown item."""
    voyage_id: int = Field(..., description="Unique voyage identifier")
    voyage_name: str = Field(..., description="Name of the expedition")
    revenue_paise: int = Field(..., description="Effective voyage revenue in integer paise")
    date: datetime = Field(..., description="Voyage departure or completion timestamp")


class RevenueAnalyticsResponse(BaseModel):
    """Detailed revenue analytics and distribution."""
    total_revenue_paise: int = Field(..., description="Total gross revenue across filtered voyages in integer paise")
    average_revenue_paise: int = Field(..., description="Average revenue per completed voyage (integer floor division)")
    highest_revenue_paise: int = Field(..., description="Highest single voyage revenue in integer paise")
    by_voyage: List[RevenueByVoyageItem] = Field(default_factory=list, description="Per-voyage revenue items")


class ExpenseCategoryItem(BaseModel):
    """Category-level expense aggregate."""
    category: str = Field(..., description="Operational cost category (e.g. Repairs, Gunpowder, Provisions)")
    amount_paise: int = Field(..., description="Total spent in category in integer paise")
    percentage_basis_points: int = Field(..., description="Share of total expenses in integer basis points (10000 = 100.00%)")


class ExpenseByVoyageItem(BaseModel):
    """Voyage expense aggregate."""
    voyage_id: int = Field(..., description="Voyage ID")
    voyage_name: str = Field(..., description="Voyage Name")
    amount_paise: int = Field(..., description="Total expenses for voyage in integer paise")


class ExpenseAnalyticsResponse(BaseModel):
    """Consolidated expense analytics."""
    total_expenses_paise: int = Field(..., description="Total operational expenses in integer paise")
    by_category: List[ExpenseCategoryItem] = Field(default_factory=list, description="Category-wise expenditure")
    by_voyage: List[ExpenseByVoyageItem] = Field(default_factory=list, description="Voyage-wise expenditure")


class ExpenseBreakdownItem(BaseModel):
    """Category breakdown item for doughnut and pie charts."""
    category: str = Field(..., description="Expense category name")
    amount_paise: int = Field(..., description="Total expense amount in integer paise")
    percentage_basis_points: int = Field(..., description="Percentage in integer basis points (10000 = 100%)")


class ExpenseBreakdownResponse(BaseModel):
    """Response containing category percentage breakdowns."""
    items: List[ExpenseBreakdownItem] = Field(default_factory=list)


class ProfitAnalyticsResponse(BaseModel):
    """Detailed profit overview and voyage performance categorization."""
    total_revenue_paise: int = Field(..., description="Total gross revenue in integer paise")
    total_expenses_paise: int = Field(..., description="Total expenses in integer paise")
    net_profit_paise: int = Field(..., description="Net profit in integer paise")
    distributable_profit_paise: int = Field(..., description="Distributable profit in integer paise")
    profitable_voyages: int = Field(..., description="Count of expeditions where net profit > 0")
    loss_making_voyages: int = Field(..., description="Count of expeditions where net profit < 0")
    break_even_voyages: int = Field(..., description="Count of expeditions where net profit == 0")
    average_profit_margin_basis_points: int = Field(..., description="Average margin across voyages in basis points")


class VoyageProfitabilityItem(BaseModel):
    """Profitability metric record for an individual voyage."""
    voyage_id: int = Field(..., description="Voyage ID")
    voyage_name: str = Field(..., description="Voyage Name")
    date: datetime = Field(..., description="Departure/log date")
    revenue_paise: int = Field(..., description="Gross revenue in integer paise")
    expenses_paise: int = Field(..., description="Operational costs in integer paise")
    net_profit_paise: int = Field(..., description="Net profit in integer paise")
    status: str = Field(..., description="Profitability status: 'PROFITABLE', 'BREAK_EVEN', or 'LOSS'")
    roi_basis_points: Optional[int] = Field(None, description="Return on investment in basis points (None if expenses == 0)")


class VoyageProfitabilityResponse(BaseModel):
    """List of voyage profitability records."""
    voyages: List[VoyageProfitabilityItem] = Field(default_factory=list)


class TopVoyageItem(BaseModel):
    """Top performing voyage item."""
    voyage_id: int
    voyage_name: str
    date: datetime
    revenue_paise: int
    expenses_paise: int
    net_profit_paise: int


class TopVoyagesResponse(BaseModel):
    """List of highest profit voyages."""
    voyages: List[TopVoyageItem] = Field(default_factory=list)


class LossVoyagesResponse(BaseModel):
    """List of voyages that incurred a loss."""
    voyages: List[TopVoyageItem] = Field(default_factory=list)


class CrewEarningsItem(BaseModel):
    """Crew member cumulative earnings from finalized payouts."""
    crew_member_id: int = Field(..., description="Crew member ID")
    name: str = Field(..., description="Pirate Name")
    rank: str = Field(..., description="Current Rank Title")
    total_earnings_paise: int = Field(..., description="Lifetime dividend payouts in integer paise")
    payout_count: int = Field(..., description="Number of finalized payout allocations received")


class CrewEarningsResponse(BaseModel):
    """List of crew earnings analytics."""
    crew: List[CrewEarningsItem] = Field(default_factory=list)


class RankPayoutItem(BaseModel):
    """Rank-level payout distribution summary."""
    rank_id: int = Field(..., description="Rank ID")
    rank: str = Field(..., description="Rank Title (e.g. Captain, First Mate)")
    share_weight_units: int = Field(..., description="Current configured share weight in integer units")
    crew_count: int = Field(..., description="Number of crew members with this rank")
    total_payout_paise: int = Field(..., description="Total finalized dividends paid to this rank in integer paise")
    payout_count: int = Field(..., description="Total count of individual dividend allocations")


class RankPayoutsResponse(BaseModel):
    """Rank-wise aggregated payout data."""
    ranks: List[RankPayoutItem] = Field(default_factory=list)


class TimeSeriesPoint(BaseModel):
    """Financial aggregation for a given time period."""
    period: str = Field(..., description="Period identifier (e.g. '2026-09-11', '2026-W37', '2026-09')")
    revenue_paise: int = Field(..., description="Gross revenue recorded in period in integer paise")
    expenses_paise: int = Field(..., description="Operational costs in period in integer paise")
    net_profit_paise: int = Field(..., description="Net profit in period in integer paise")


class TimeSeriesResponse(BaseModel):
    """Time-series dataset for Chart.js line and bar trends."""
    group_by: str = Field(..., description="Granularity: 'daily', 'weekly', or 'monthly'")
    data: List[TimeSeriesPoint] = Field(default_factory=list)


class PayoutVoyageSummary(BaseModel):
    """Payout summary for a single voyage."""
    voyage_id: int
    voyage_name: str
    total_payout_paise: int
    crew_count: int


class PayoutRankSummary(BaseModel):
    """Payout summary grouped by rank name."""
    rank: str
    total_payout_paise: int
    payout_count: int


class PayoutAnalyticsResponse(BaseModel):
    """Consolidated dividend payout analytics."""
    total_payouts_paise: int = Field(..., description="Total finalized dividend distributions in integer paise")
    payout_count: int = Field(..., description="Total individual dividend records created")
    average_payout_paise: int = Field(..., description="Average payout per allocation (integer floor division)")
    by_voyage: List[PayoutVoyageSummary] = Field(default_factory=list)
    by_rank: List[PayoutRankSummary] = Field(default_factory=list)


class RevenueExpensePoint(BaseModel):
    """Single data point comparing revenue, expenses, and net profit for Chart.js."""
    label: str = Field(..., description="Voyage name or date interval label")
    revenue_paise: int = Field(..., description="Gross revenue in integer paise")
    expenses_paise: int = Field(..., description="Operational costs in integer paise")
    net_profit_paise: int = Field(..., description="Net profit in integer paise")


class RevenueExpenseResponse(BaseModel):
    """Pre-formatted response structure optimized for Chart.js bar and line charts."""
    labels: List[str] = Field(default_factory=list, description="X-axis category labels")
    data: List[RevenueExpensePoint] = Field(default_factory=list, description="Structured dataset points")


class PaginationParams(BaseModel):
    """Query parameter pagination contract."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized wrapper for paginated API responses."""
    items: List[T] = Field(default_factory=list)
    total: int = Field(..., description="Total number of matching records")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total available pages")
