"""
API Router for Treasury Dashboard KPIs, Financial Analytics, and Chart.js Feeds.
Provides comprehensive financial intelligence, time-series distributions,
profitability rankings, and dividend histories.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.analytics import (
    DashboardSummaryResponse,
    RevenueAnalyticsResponse,
    ExpenseAnalyticsResponse,
    ExpenseBreakdownResponse,
    ProfitAnalyticsResponse,
    VoyageProfitabilityItem,
    TopVoyagesResponse,
    LossVoyagesResponse,
    CrewEarningsItem,
    RankPayoutsResponse,
    TimeSeriesPoint,
    TimeSeriesResponse,
    PayoutAnalyticsResponse,
    PaginatedResponse,
)
from backend.services.analytics_service import (
    get_dashboard_summary,
    get_revenue_analytics,
    get_expense_analytics,
    get_expense_category_breakdown,
    get_profit_analytics,
    get_voyages_profitability,
    get_top_voyages,
    get_loss_making_voyages,
    get_crew_earnings_analytics,
    get_rank_payout_analytics,
    get_time_series_analytics,
    get_payout_analytics,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Dashboard"])


def _verify_analytics_role(role: Optional[str] = None, allow_crew: bool = True) -> str:
    """Validate user role for analytics access."""
    active_role = (role or "captain").lower().strip()
    allowed_roles = ["admin", "captain"]
    if allow_crew:
        allowed_roles.append("crew")

    if active_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized to access treasury analytics."
        )
    return active_role


@router.get(
    "/dashboard-summary",
    response_model=DashboardSummaryResponse,
    summary="High-Level Treasury Dashboard KPIs",
    description="Retrieve consolidated treasury summary including total revenue, expenses, net profit, distributable dividends, voyage counts, and active crew."
)
def read_dashboard_summary(
    start_date: Optional[datetime] = Query(None, description="Filter records starting on or after date"),
    end_date: Optional[datetime] = Query(None, description="Filter records ending on or before date"),
    voyage_id: Optional[int] = Query(None, description="Optional single voyage filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    data = get_dashboard_summary(db, start_date=start_date, end_date=end_date, voyage_id=voyage_id)
    return DashboardSummaryResponse(**data)


@router.get(
    "/revenue",
    response_model=RevenueAnalyticsResponse,
    summary="Revenue Analytics & Distributions",
    description="Retrieve total revenue, deterministic average revenue per completed voyage, highest revenue voyage, and itemized voyage revenue list."
)
def read_revenue_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    data = get_revenue_analytics(db, start_date=start_date, end_date=end_date)
    return RevenueAnalyticsResponse(**data)


@router.get(
    "/expenses",
    response_model=ExpenseAnalyticsResponse,
    summary="Expense Analytics & Distributions",
    description="Retrieve total expenses, category-wise expenditure in paise and basis points, and voyage-level costs."
)
def read_expense_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    voyage_id: Optional[int] = Query(None, description="Optional voyage filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    data = get_expense_analytics(db, start_date=start_date, end_date=end_date, voyage_id=voyage_id)
    return ExpenseAnalyticsResponse(**data)


@router.get(
    "/expenses/by-category",
    response_model=ExpenseBreakdownResponse,
    summary="Expense Category Percentage Breakdown",
    description="Retrieve itemized expense category amounts and percentage basis points for Chart.js doughnut and pie charts."
)
def read_expense_by_category(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    voyage_id: Optional[int] = Query(None, description="Optional voyage filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    items = get_expense_category_breakdown(db, start_date=start_date, end_date=end_date, voyage_id=voyage_id)
    return ExpenseBreakdownResponse(items=items)


@router.get(
    "/profit",
    response_model=ProfitAnalyticsResponse,
    summary="Profit Analytics & Performance Metrics",
    description="Retrieve net profit, distributable profit, profitable vs loss-making voyage counts, and profit margin in basis points."
)
def read_profit_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    data = get_profit_analytics(db, start_date=start_date, end_date=end_date)
    return ProfitAnalyticsResponse(**data)


@router.get(
    "/voyages/profitability",
    response_model=PaginatedResponse[VoyageProfitabilityItem],
    summary="Voyage Profitability & ROI Rankings",
    description="Retrieve per-voyage profitability metrics, status classification (PROFITABLE, BREAK_EVEN, LOSS), and ROI basis points."
)
def read_voyages_profitability(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    sort_by: str = Query("date", description="Sort field: 'date', 'revenue_paise', 'expenses_paise', 'net_profit_paise', 'name'"),
    order: str = Query("desc", description="'asc' or 'desc'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    data = get_voyages_profitability(
        db,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size
    )
    return PaginatedResponse[VoyageProfitabilityItem](
        items=[VoyageProfitabilityItem(**v) for v in data["voyages"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get(
    "/voyages/top",
    response_model=TopVoyagesResponse,
    summary="Top-Performing Expeditions",
    description="Retrieve highest net profit voyages ranked in descending order."
)
def read_top_voyages(
    limit: int = Query(5, ge=1, le=50, description="Maximum number of voyages to return"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    items = get_top_voyages(db, limit=limit, start_date=start_date, end_date=end_date)
    return TopVoyagesResponse(voyages=items)


@router.get(
    "/voyages/losses",
    response_model=LossVoyagesResponse,
    summary="Loss-Making Expeditions",
    description="Retrieve expeditions operating at a loss (net_profit_paise < 0), ordered by largest loss first."
)
def read_loss_making_voyages(
    limit: Optional[int] = Query(None, ge=1, le=50, description="Optional maximum limit"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    items = get_loss_making_voyages(db, limit=limit, start_date=start_date, end_date=end_date)
    return LossVoyagesResponse(voyages=items)


@router.get(
    "/crew/earnings",
    response_model=PaginatedResponse[CrewEarningsItem],
    summary="Crew Member Lifetime Earnings Leaderboard",
    description="Retrieve cumulative finalized dividend earnings for crew members from historical payout records."
)
def read_crew_earnings_analytics(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("earnings", description="Sort field: 'earnings', 'name', 'payout_count'"),
    order: str = Query("desc", description="'asc' or 'desc'"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    data = get_crew_earnings_analytics(db, page=page, page_size=page_size, sort_by=sort_by, order=order)
    return PaginatedResponse[CrewEarningsItem](
        items=[CrewEarningsItem(**c) for c in data["crew"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get(
    "/ranks/payouts",
    response_model=RankPayoutsResponse,
    summary="Rank-Wise Payout Aggregation",
    description="Retrieve total dividend payouts, crew distribution, and allocation counts grouped by pirate rank."
)
def read_rank_payout_analytics(
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    ranks = get_rank_payout_analytics(db)
    return RankPayoutsResponse(ranks=ranks)


@router.get(
    "/time-series",
    response_model=TimeSeriesResponse,
    summary="Time-Series Revenue, Expense, and Profit Trends",
    description="Retrieve time-series financial aggregates grouped by 'daily', 'weekly', or 'monthly' periods for Chart.js line and bar charts."
)
def read_time_series_analytics(
    group_by: str = Query("monthly", description="Granularity: 'daily', 'weekly', or 'monthly'"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    points = get_time_series_analytics(db, group_by=group_by, start_date=start_date, end_date=end_date)
    return TimeSeriesResponse(
        group_by=group_by.lower().strip(),
        data=[TimeSeriesPoint(**p) for p in points]
    )


@router.get(
    "/payouts",
    response_model=PayoutAnalyticsResponse,
    summary="Consolidated Dividend Payout Analytics",
    description="Retrieve total finalized payouts, allocation count, deterministic average payout, and breakdowns by voyage and rank."
)
def read_payout_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    voyage_id: Optional[int] = Query(None, description="Optional voyage filter"),
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_analytics_role(x_user_role, allow_crew=True)
    data = get_payout_analytics(db, start_date=start_date, end_date=end_date, voyage_id=voyage_id)
    return PayoutAnalyticsResponse(**data)
