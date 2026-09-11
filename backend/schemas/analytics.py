"""
Pydantic schemas for Treasury Dashboard KPIs, Chart.js visual contracts, and financial analytics.
"""

from typing import List, Optional, Generic, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class DashboardKPIs(BaseModel):
    """Aggregated financial snapshot for the Captain's Dashboard KPI cards."""
    total_revenue_paise: int = Field(..., description="Cumulative gross revenue across all voyages in integer paise")
    total_expenses_paise: int = Field(..., description="Cumulative operational expenses in integer paise")
    net_profit_paise: int = Field(..., description="Total treasury net profit in integer paise")
    total_distributed_paise: int = Field(..., description="Total dividends distributed to crew in integer paise")
    active_crew_count: int = Field(..., description="Number of active crew members aboard")
    completed_voyage_count: int = Field(..., description="Number of completed expeditions")


class RevenueExpensePoint(BaseModel):
    """Single data point comparing revenue, expenses, and net profit for a voyage or time period."""
    label: str = Field(..., description="Voyage name or date interval label")
    revenue_paise: int = Field(..., description="Gross revenue in integer paise")
    expenses_paise: int = Field(..., description="Operational costs in integer paise")
    net_profit_paise: int = Field(..., description="Net profit in integer paise")


class RevenueExpenseResponse(BaseModel):
    """Pre-formatted response structure optimized for Chart.js bar and line charts."""
    labels: List[str] = Field(default_factory=list, description="X-axis category labels")
    data: List[RevenueExpensePoint] = Field(default_factory=list, description="Structured dataset points")


class ExpenseBreakdownItem(BaseModel):
    """Category-level aggregation for doughnut and pie charts."""
    category: str = Field(..., description="Expense category name (e.g. Ship Repair, Gunpowder)")
    amount_paise: int = Field(..., description="Total expenses in category in integer paise")
    percentage_basis_points: int = Field(..., description="Percentage in integer basis points (e.g. 3500 = 35.00%)")


class ExpenseBreakdownResponse(BaseModel):
    """Response structure containing itemized expense category breakdowns."""
    items: List[ExpenseBreakdownItem] = Field(default_factory=list)


class ProfitAnalyticsResponse(BaseModel):
    """Summary profit analytics and margin statistics."""
    total_profit_paise: int = Field(..., description="Total cumulative net profit")
    average_profit_paise: int = Field(..., description="Average profit per voyage in integer paise")
    highest_profit_paise: int = Field(..., description="Maximum single-voyage profit in integer paise")
    lowest_profit_paise: int = Field(..., description="Minimum single-voyage profit/loss in integer paise")
    highest_profit_voyage_id: Optional[int] = Field(None, description="Voyage ID that yielded highest profit")
    average_profit_margin_basis_points: int = Field(..., description="Average margin across voyages in basis points")


class CrewEarningsItem(BaseModel):
    """Individual pirate lifetime earnings row."""
    crew_member_id: int
    crew_member_name: str
    rank_name: str
    total_earnings_paise: int = Field(..., description="Lifetime dividend payouts received in integer paise")


class CrewEarningsResponse(BaseModel):
    """Rank-wise or top-earner list for crew earnings charts and tables."""
    items: List[CrewEarningsItem] = Field(default_factory=list)


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
