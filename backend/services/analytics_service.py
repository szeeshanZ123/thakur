"""
Analytics Service for Captain's Treasure Ledger.
Computes treasury KPIs, financial aggregations, time-series data, expense category distributions,
voyage profitability rankings, and crew/rank payout summaries.

CRITICAL FINANCIAL RULES:
- All monetary values are strictly INTEGER PAISE.
- Percentages & margins are strictly INTEGER BASIS POINTS (10000 = 100.00%).
- All revenue and expense totals reconcile directly with the Phase 5 TransactionLog.
- All crew dividends reconcile directly with Phase 6 Payout records.
- Handles empty database state safely with zeroed metrics (no exceptions).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import math
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog
from backend.models.crew import CrewMember
from backend.models.rank import Rank
from backend.models.payout import Payout
from backend.services.financial_service import (
    calculate_voyage_effective_revenue,
    calculate_voyage_effective_expenses,
    calculate_net_profit,
    calculate_distributable_profit,
)


def _validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> None:
    """Validate that start_date does not exceed end_date."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be greater than end_date."
        )


def _get_filtered_voyages(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    voyage_id: Optional[int] = None
) -> List[Voyage]:
    """Retrieve voyages matching optional date range and voyage ID filters."""
    query = db.query(Voyage).options(joinedload(Voyage.expenses))
    if voyage_id is not None:
        query = query.filter(Voyage.id == voyage_id)
    if start_date is not None:
        query = query.filter(Voyage.date >= start_date)
    if end_date is not None:
        query = query.filter(Voyage.date <= end_date)
    return query.order_by(Voyage.date.asc()).all()


def get_dashboard_summary(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    voyage_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate high-level treasury KPI summary.
    All monetary fields are exact integer paise.
    """
    _validate_date_range(start_date, end_date)
    voyages = _get_filtered_voyages(db, start_date, end_date, voyage_id)

    total_revenue_paise = 0
    total_expenses_paise = 0
    completed_voyages = 0
    ongoing_voyages = 0
    planned_voyages = 0

    for v in voyages:
        rev = calculate_voyage_effective_revenue(db, v.id)
        exp = calculate_voyage_effective_expenses(db, v.id)
        total_revenue_paise += rev
        total_expenses_paise += exp

        if v.status == "completed":
            completed_voyages += 1
        elif v.status == "ongoing":
            ongoing_voyages += 1
        elif v.status == "planned":
            planned_voyages += 1

    net_profit_paise = total_revenue_paise - total_expenses_paise
    distributable_profit_paise = max(0, net_profit_paise)

    # Calculate total payouts from finalized records
    payout_query = db.query(Payout)
    if voyage_id is not None:
        payout_query = payout_query.filter(Payout.voyage_id == voyage_id)
    elif start_date or end_date:
        v_ids = [v.id for v in voyages]
        payout_query = payout_query.filter(Payout.voyage_id.in_(v_ids)) if v_ids else payout_query.filter(Payout.id == -1)

    all_payouts = payout_query.all()
    total_payouts_paise = sum(p.payout_paise for p in all_payouts)

    active_crew = db.query(CrewMember).filter(CrewMember.is_active == True).count()

    return {
        "total_revenue_paise": total_revenue_paise,
        "total_expenses_paise": total_expenses_paise,
        "net_profit_paise": net_profit_paise,
        "distributable_profit_paise": distributable_profit_paise,
        "total_payouts_paise": total_payouts_paise,
        "total_voyages": len(voyages),
        "completed_voyages": completed_voyages,
        "ongoing_voyages": ongoing_voyages,
        "planned_voyages": planned_voyages,
        "active_crew": active_crew,
    }


def get_revenue_analytics(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Generate revenue distribution and metrics.
    Average revenue uses deterministic integer floor division.
    """
    _validate_date_range(start_date, end_date)
    voyages = _get_filtered_voyages(db, start_date, end_date)

    total_revenue_paise = 0
    highest_revenue_paise = 0
    by_voyage = []
    completed_count = 0

    for v in voyages:
        rev = calculate_voyage_effective_revenue(db, v.id)
        total_revenue_paise += rev
        if rev > highest_revenue_paise:
            highest_revenue_paise = rev

        if v.status == "completed":
            completed_count += 1

        by_voyage.append({
            "voyage_id": v.id,
            "voyage_name": v.name,
            "revenue_paise": rev,
            "date": v.date,
        })

    # Average per completed voyage, fallback to all voyages
    divisor = completed_count if completed_count > 0 else (len(voyages) if voyages else 0)
    average_revenue_paise = (total_revenue_paise // divisor) if divisor > 0 else 0

    return {
        "total_revenue_paise": total_revenue_paise,
        "average_revenue_paise": average_revenue_paise,
        "highest_revenue_paise": highest_revenue_paise,
        "by_voyage": by_voyage,
    }


def get_expense_analytics(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    voyage_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate expense metrics, itemized by category and by voyage.
    """
    _validate_date_range(start_date, end_date)
    voyages = _get_filtered_voyages(db, start_date, end_date, voyage_id)

    total_expenses_paise = 0
    by_voyage = []

    for v in voyages:
        exp = calculate_voyage_effective_expenses(db, v.id)
        total_expenses_paise += exp
        by_voyage.append({
            "voyage_id": v.id,
            "voyage_name": v.name,
            "amount_paise": exp,
        })

    # Category Breakdown
    v_ids = [v.id for v in voyages]
    if v_ids:
        all_expenses = db.query(Expense).filter(Expense.voyage_id.in_(v_ids)).all()
    else:
        all_expenses = []

    cat_map: Dict[str, int] = {}
    for e in all_expenses:
        cat_map[e.category] = cat_map.get(e.category, 0) + e.amount_paise

    by_category = []
    for cat, amount in sorted(cat_map.items()):
        bps = (amount * 10000 // total_expenses_paise) if total_expenses_paise > 0 else 0
        by_category.append({
            "category": cat,
            "amount_paise": amount,
            "percentage_basis_points": bps,
        })

    return {
        "total_expenses_paise": total_expenses_paise,
        "by_category": by_category,
        "by_voyage": by_voyage,
    }


def get_expense_category_breakdown(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    voyage_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Generate category breakdown list for Chart.js doughnut / pie charts.
    """
    analytics = get_expense_analytics(db, start_date, end_date, voyage_id)
    return analytics["by_category"]


def get_profit_analytics(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Analyze net profit, margins, and voyage classification (profitable, break-even, loss).
    """
    _validate_date_range(start_date, end_date)
    voyages = _get_filtered_voyages(db, start_date, end_date)

    total_revenue_paise = 0
    total_expenses_paise = 0
    profitable_count = 0
    loss_count = 0
    break_even_count = 0

    for v in voyages:
        rev = calculate_voyage_effective_revenue(db, v.id)
        exp = calculate_voyage_effective_expenses(db, v.id)
        profit = rev - exp

        total_revenue_paise += rev
        total_expenses_paise += exp

        if profit > 0:
            profitable_count += 1
        elif profit < 0:
            loss_count += 1
        else:
            break_even_count += 1

    net_profit_paise = total_revenue_paise - total_expenses_paise
    distributable_profit_paise = max(0, net_profit_paise)

    avg_margin_bps = (net_profit_paise * 10000 // total_revenue_paise) if total_revenue_paise > 0 else 0

    return {
        "total_revenue_paise": total_revenue_paise,
        "total_expenses_paise": total_expenses_paise,
        "net_profit_paise": net_profit_paise,
        "distributable_profit_paise": distributable_profit_paise,
        "profitable_voyages": profitable_count,
        "loss_making_voyages": loss_count,
        "break_even_voyages": break_even_count,
        "average_profit_margin_basis_points": avg_margin_bps,
    }


def get_voyages_profitability(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: str = "date",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Compute profitability and ROI for each voyage with sorting and pagination.
    """
    _validate_date_range(start_date, end_date)
    voyages = _get_filtered_voyages(db, start_date, end_date)

    results = []
    for v in voyages:
        rev = calculate_voyage_effective_revenue(db, v.id)
        exp = calculate_voyage_effective_expenses(db, v.id)
        profit = rev - exp

        if profit > 0:
            status_str = "PROFITABLE"
        elif profit < 0:
            status_str = "LOSS"
        else:
            status_str = "BREAK_EVEN"

        roi_bps = (profit * 10000 // exp) if exp > 0 else None

        results.append({
            "voyage_id": v.id,
            "voyage_name": v.name,
            "date": v.date,
            "revenue_paise": rev,
            "expenses_paise": exp,
            "net_profit_paise": profit,
            "status": status_str,
            "roi_basis_points": roi_bps,
        })

    # Safe allowlist sorting
    is_reverse = (order.lower() == "desc")
    if sort_by == "net_profit_paise":
        results.sort(key=lambda x: x["net_profit_paise"], reverse=is_reverse)
    elif sort_by == "revenue_paise":
        results.sort(key=lambda x: x["revenue_paise"], reverse=is_reverse)
    elif sort_by == "expenses_paise":
        results.sort(key=lambda x: x["expenses_paise"], reverse=is_reverse)
    elif sort_by == "name":
        results.sort(key=lambda x: x["voyage_name"].lower(), reverse=is_reverse)
    else:  # default to date
        results.sort(key=lambda x: x["date"], reverse=is_reverse)

    total = len(results)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    start_idx = (page - 1) * page_size
    paged_items = results[start_idx : start_idx + page_size]

    return {
        "voyages": paged_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_top_voyages(
    db: Session,
    limit: int = 5,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Identify top-performing expeditions ranked by net_profit_paise descending.
    """
    _validate_date_range(start_date, end_date)
    voyages = _get_filtered_voyages(db, start_date, end_date)

    items = []
    for v in voyages:
        rev = calculate_voyage_effective_revenue(db, v.id)
        exp = calculate_voyage_effective_expenses(db, v.id)
        profit = rev - exp
        items.append({
            "voyage_id": v.id,
            "voyage_name": v.name,
            "date": v.date,
            "revenue_paise": rev,
            "expenses_paise": exp,
            "net_profit_paise": profit,
        })

    items.sort(key=lambda x: x["net_profit_paise"], reverse=True)
    return items[:limit]


def get_loss_making_voyages(
    db: Session,
    limit: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve expeditions that operated at a loss (net_profit_paise < 0),
    sorted by largest loss first (net_profit_paise ascending).
    """
    _validate_date_range(start_date, end_date)
    voyages = _get_filtered_voyages(db, start_date, end_date)

    losses = []
    for v in voyages:
        rev = calculate_voyage_effective_revenue(db, v.id)
        exp = calculate_voyage_effective_expenses(db, v.id)
        profit = rev - exp
        if profit < 0:
            losses.append({
                "voyage_id": v.id,
                "voyage_name": v.name,
                "date": v.date,
                "revenue_paise": rev,
                "expenses_paise": exp,
                "net_profit_paise": profit,
            })

    losses.sort(key=lambda x: x["net_profit_paise"])  # most negative first
    if limit is not None:
        losses = losses[:limit]
    return losses


def get_crew_earnings_analytics(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "earnings",
    order: str = "desc"
) -> Dict[str, Any]:
    """
    Aggregate lifetime finalized earnings for all crew members.
    Reconciles with Phase 6 Payout records without recalculating from current weights.
    """
    crew_members = db.query(CrewMember).options(
        joinedload(CrewMember.rank),
        joinedload(CrewMember.payouts)
    ).all()

    crew_list = []
    for c in crew_members:
        earnings = sum(p.payout_paise for p in c.payouts)
        payout_count = len(c.payouts)
        crew_list.append({
            "crew_member_id": c.id,
            "name": c.name,
            "rank": c.rank.name if c.rank else "Unassigned",
            "total_earnings_paise": earnings,
            "payout_count": payout_count,
        })

    is_reverse = (order.lower() == "desc")
    if sort_by == "name":
        crew_list.sort(key=lambda x: x["name"].lower(), reverse=is_reverse)
    elif sort_by == "payout_count":
        crew_list.sort(key=lambda x: x["payout_count"], reverse=is_reverse)
    else:  # default to earnings
        crew_list.sort(key=lambda x: x["total_earnings_paise"], reverse=is_reverse)

    total = len(crew_list)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    start_idx = (page - 1) * page_size
    paged_items = crew_list[start_idx : start_idx + page_size]

    return {
        "crew": paged_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_rank_payout_analytics(db: Session) -> List[Dict[str, Any]]:
    """
    Aggregate payout totals and crew distribution by pirate rank.
    """
    ranks = db.query(Rank).options(joinedload(Rank.crew_members)).all()
    all_payouts = db.query(Payout).options(joinedload(Payout.crew_member)).all()

    # Map crew_member_id to rank_id
    crew_rank_map = {}
    for r in ranks:
        for c in r.crew_members:
            crew_rank_map[c.id] = r.id

    rank_payout_paise: Dict[int, int] = {}
    rank_payout_count: Dict[int, int] = {}

    for p in all_payouts:
        r_id = crew_rank_map.get(p.crew_member_id)
        if r_id is not None:
            rank_payout_paise[r_id] = rank_payout_paise.get(r_id, 0) + p.payout_paise
            rank_payout_count[r_id] = rank_payout_count.get(r_id, 0) + 1

    items = []
    for r in ranks:
        items.append({
            "rank_id": r.id,
            "rank": r.name,
            "share_weight_units": r.share_weight_units,
            "crew_count": len(r.crew_members),
            "total_payout_paise": rank_payout_paise.get(r.id, 0),
            "payout_count": rank_payout_count.get(r.id, 0),
        })

    items.sort(key=lambda x: x["total_payout_paise"], reverse=True)
    return items


def get_time_series_analytics(
    db: Session,
    group_by: str = "monthly",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Group revenue, expenses, and net profit over daily, weekly, or monthly periods.
    """
    _validate_date_range(start_date, end_date)
    granularity = group_by.lower().strip()
    if granularity not in ["daily", "weekly", "monthly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by must be one of: 'daily', 'weekly', 'monthly'."
        )

    voyages = _get_filtered_voyages(db, start_date, end_date)

    period_data: Dict[str, Dict[str, int]] = {}

    for v in voyages:
        if granularity == "daily":
            period_key = v.date.strftime("%Y-%m-%d")
        elif granularity == "weekly":
            period_key = f"{v.date.year}-W{v.date.isocalendar()[1]:02d}"
        else:  # monthly
            period_key = v.date.strftime("%Y-%m")

        rev = calculate_voyage_effective_revenue(db, v.id)
        exp = calculate_voyage_effective_expenses(db, v.id)

        if period_key not in period_data:
            period_data[period_key] = {"revenue_paise": 0, "expenses_paise": 0}

        period_data[period_key]["revenue_paise"] += rev
        period_data[period_key]["expenses_paise"] += exp

    points = []
    for period in sorted(period_data.keys()):
        r = period_data[period]["revenue_paise"]
        e = period_data[period]["expenses_paise"]
        p = r - e
        points.append({
            "period": period,
            "revenue_paise": r,
            "expenses_paise": e,
            "net_profit_paise": p,
        })

    return points


def get_payout_analytics(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    voyage_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Consolidated payout statistics across voyages and ranks.
    """
    _validate_date_range(start_date, end_date)
    query = db.query(Payout).options(
        joinedload(Payout.voyage),
        joinedload(Payout.crew_member).joinedload(CrewMember.rank)
    )

    if voyage_id is not None:
        query = query.filter(Payout.voyage_id == voyage_id)
    elif start_date or end_date:
        voyages = _get_filtered_voyages(db, start_date, end_date)
        v_ids = [v.id for v in voyages]
        query = query.filter(Payout.voyage_id.in_(v_ids)) if v_ids else query.filter(Payout.id == -1)

    payouts = query.all()
    total_payouts_paise = sum(p.payout_paise for p in payouts)
    payout_count = len(payouts)
    average_payout_paise = (total_payouts_paise // payout_count) if payout_count > 0 else 0

    # Group by voyage
    voyage_map: Dict[int, Dict[str, Any]] = {}
    for p in payouts:
        v_id = p.voyage_id
        if v_id not in voyage_map:
            voyage_map[v_id] = {
                "voyage_id": v_id,
                "voyage_name": p.voyage.name if p.voyage else f"Voyage #{v_id}",
                "total_payout_paise": 0,
                "crew_ids": set(),
            }
        voyage_map[v_id]["total_payout_paise"] += p.payout_paise
        voyage_map[v_id]["crew_ids"].add(p.crew_member_id)

    by_voyage = [
        {
            "voyage_id": v["voyage_id"],
            "voyage_name": v["voyage_name"],
            "total_payout_paise": v["total_payout_paise"],
            "crew_count": len(v["crew_ids"]),
        }
        for v in voyage_map.values()
    ]

    # Group by rank
    rank_map: Dict[str, Dict[str, Any]] = {}
    for p in payouts:
        rank_name = p.crew_member.rank.name if (p.crew_member and p.crew_member.rank) else "Unassigned"
        if rank_name not in rank_map:
            rank_map[rank_name] = {"rank": rank_name, "total_payout_paise": 0, "payout_count": 0}
        rank_map[rank_name]["total_payout_paise"] += p.payout_paise
        rank_map[rank_name]["payout_count"] += 1

    by_rank = list(rank_map.values())

    return {
        "total_payouts_paise": total_payouts_paise,
        "payout_count": payout_count,
        "average_payout_paise": average_payout_paise,
        "by_voyage": by_voyage,
        "by_rank": by_rank,
    }
