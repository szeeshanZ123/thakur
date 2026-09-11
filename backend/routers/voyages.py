"""
API Router for Voyages & Expeditions Management.
"""

from typing import List, Optional
from datetime import datetime
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.core.database import get_db
from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog
from backend.models.payout import Payout
from backend.schemas.voyage import (
    VoyageCreate,
    VoyageUpdate,
    VoyageResponse,
    VoyageFinancialSummaryResponse,
    RevenuePostRequest,
)
from backend.schemas.transaction import TransactionResponse
from backend.schemas.payout import (
    PayoutPreview,
    PayoutFinalizeResponse,
    PayoutResponse,
)
from backend.schemas.analytics import PaginatedResponse
from backend.services.financial_service import (
    get_voyage_financial_summary,
    post_revenue_transaction,
    calculate_voyage_effective_revenue,
    calculate_voyage_effective_expenses,
)
from backend.services.payout_service import (
    preview_voyage_payouts,
    finalize_voyage_payouts,
    get_voyage_payouts,
)
from fastapi import Header

router = APIRouter(prefix="/api/voyages", tags=["Voyages"])



def _to_voyage_response(voyage: Voyage, db: Optional[Session] = None) -> VoyageResponse:
    """Helper to convert Voyage ORM entity to VoyageResponse with calculated metrics."""
    if db:
        revenue = calculate_voyage_effective_revenue(db, voyage.id)
        total_expenses = calculate_voyage_effective_expenses(db, voyage.id)
    else:
        revenue = voyage.revenue_paise
        total_expenses = sum(e.amount_paise for e in voyage.expenses) if voyage.expenses else 0
    net_profit = revenue - total_expenses
    margin_bps = (net_profit * 10000 // revenue) if revenue > 0 else 0

    return VoyageResponse(
        id=voyage.id,
        name=voyage.name,
        date=voyage.date,
        description=voyage.description,
        revenue_paise=revenue,
        status=voyage.status,
        total_expenses_paise=total_expenses,
        net_profit_paise=net_profit,
        profit_margin_basis_points=margin_bps,
        created_at=voyage.created_at,
        updated_at=voyage.updated_at
    )


@router.get("", response_model=PaginatedResponse[VoyageResponse], summary="List voyages with search and date filters")
def list_voyages(
    search: Optional[str] = Query(None, description="Search by voyage name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (planned, ongoing, completed, cancelled)"),
    date_from: Optional[datetime] = Query(None, description="Filter departure date on or after"),
    date_to: Optional[datetime] = Query(None, description="Filter departure date on or before"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated voyages with optional name search, status, and date range filters."""
    query = db.query(Voyage).options(joinedload(Voyage.expenses))

    if search:
        query = query.filter(Voyage.name.ilike(f"%{search.strip()}%"))
    if status_filter:
        query = query.filter(Voyage.status == status_filter)
    if date_from:
        query = query.filter(Voyage.date >= date_from)
    if date_to:
        query = query.filter(Voyage.date <= date_to)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    voyage_records = query.order_by(Voyage.date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = [_to_voyage_response(v, db) for v in voyage_records]
    return PaginatedResponse[VoyageResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("", response_model=VoyageResponse, status_code=status.HTTP_201_CREATED, summary="Log a new voyage")
def create_voyage(
    payload: VoyageCreate,
    db: Session = Depends(get_db)
):
    """Create a new expedition record with gross loot revenue in integer paise."""
    voyage = Voyage(
        name=payload.name,
        date=payload.date,
        description=payload.description,
        revenue_paise=payload.revenue_paise,
        status=payload.status
    )
    db.add(voyage)
    db.commit()
    db.refresh(voyage)

    return _to_voyage_response(voyage, db)


@router.get("/{voyage_id}", response_model=VoyageResponse, summary="Get voyage by ID")
def get_voyage(
    voyage_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve detailed voyage metrics, gross revenue, and operational expenses."""
    voyage = db.query(Voyage).options(joinedload(Voyage.expenses)).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )
    return _to_voyage_response(voyage, db)


@router.put("/{voyage_id}", response_model=VoyageResponse, summary="Update voyage metadata")
def update_voyage(
    voyage_id: int,
    payload: VoyageUpdate,
    db: Session = Depends(get_db)
):
    """Update voyage parameters, gross revenue, or status."""
    voyage = db.query(Voyage).options(joinedload(Voyage.expenses)).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    if payload.name is not None:
        voyage.name = payload.name
    if payload.date is not None:
        voyage.date = payload.date
    if payload.description is not None:
        voyage.description = payload.description
    if payload.revenue_paise is not None:
        voyage.revenue_paise = payload.revenue_paise
    if payload.status is not None:
        voyage.status = payload.status

    db.commit()
    db.refresh(voyage)
    return _to_voyage_response(voyage, db)


@router.delete("/{voyage_id}", status_code=status.HTTP_200_OK, summary="Delete an unfinalized empty voyage")
def delete_voyage(
    voyage_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a voyage only if it contains no recorded expenses, transactions, or payouts.
    Blocks deletion (409 Conflict) if any financial records are attached.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    # Check for attached financial records
    expense_count = db.query(Expense).filter(Expense.voyage_id == voyage_id).count()
    tx_count = db.query(TransactionLog).filter(TransactionLog.voyage_id == voyage_id).count()
    payout_count = db.query(Payout).filter(Payout.voyage_id == voyage_id).count()

    if expense_count > 0 or tx_count > 0 or payout_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Voyage cannot be deleted because it contains financial records (expenses, transactions, or payouts)."
        )

    db.delete(voyage)
    db.commit()
    return {"message": f"Voyage {voyage_id} successfully deleted.", "id": voyage_id}


@router.post("/{voyage_id}/revenue/post", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED, summary="Post voyage revenue to immutable ledger")
def post_revenue(
    voyage_id: int,
    payload: Optional[RevenuePostRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Atomically post gross loot revenue for a voyage as an immutable CREDIT transaction.
    Enforces idempotency: rejects duplicate postings with HTTP 409 Conflict.
    """
    revenue_override = payload.revenue_paise if payload else None
    desc_override = payload.description if payload else None
    tx = post_revenue_transaction(
        db=db,
        voyage_id=voyage_id,
        revenue_paise=revenue_override,
        description=desc_override
    )
    return tx


@router.get("/{voyage_id}/financial-summary", response_model=VoyageFinancialSummaryResponse, summary="Get voyage financial summary")
def get_financial_summary(
    voyage_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve comprehensive financial summary in exact integer paise:
    Gross revenue, operational expenses, net profit (can be negative), and distributable profit.
    """
    summary = get_voyage_financial_summary(db=db, voyage_id=voyage_id)
    return VoyageFinancialSummaryResponse(**summary)


@router.get("/{voyage_id}/transactions", response_model=List[TransactionResponse], summary="Get chronological transactions for a voyage")
def get_voyage_transactions(
    voyage_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve chronological audit ledger transactions for a specific voyage.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    transactions = (
        db.query(TransactionLog)
        .filter(TransactionLog.voyage_id == voyage_id)
        .order_by(TransactionLog.timestamp.asc())
        .all()
    )
    return transactions


@router.post("/{voyage_id}/payouts/preview", response_model=PayoutPreview, summary="Preview voyage dividend payouts")
@router.get("/{voyage_id}/payouts/preview", response_model=PayoutPreview, summary="Preview voyage dividend payouts (GET alias)")
@router.post("/{voyage_id}/calculate-payouts", response_model=PayoutPreview, summary="Calculate dividend payouts preview (alias)")
def preview_payouts(
    voyage_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate an uncommitted, transparent dividend preview for a voyage.
    Reconciles exact zero-loss integer math across all active crew members.
    """
    preview_data = preview_voyage_payouts(db=db, voyage_id=voyage_id)
    return PayoutPreview(**preview_data)


@router.post("/{voyage_id}/payouts/finalize", response_model=PayoutFinalizeResponse, status_code=status.HTTP_201_CREATED, summary="Finalize immutable voyage dividend payouts")
@router.post("/{voyage_id}/finalize-payouts", response_model=PayoutFinalizeResponse, status_code=status.HTTP_201_CREATED, summary="Finalize dividend payouts (alias)")
def finalize_payouts(
    voyage_id: int,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role", description="User authorization role (captain, admin, crew)"),
    db: Session = Depends(get_db)
):
    """
    Atomically finalize and commit immutable dividend payouts for a completed voyage.
    Enforces Captain/Admin authorization, completed voyage status, and idempotency protection.
    """
    voyage, payouts = finalize_voyage_payouts(
        db=db,
        voyage_id=voyage_id,
        user_role=x_user_role
    )

    total_distributed = sum(p.payout_paise for p in payouts)
    payout_responses = [
        PayoutResponse(
            id=p.id,
            voyage_id=p.voyage_id,
            crew_member_id=p.crew_member_id,
            crew_member_name=p.crew_member.name if p.crew_member else None,
            rank_name=p.crew_member.rank.name if p.crew_member and p.crew_member.rank else None,
            share_weight_units_used=p.share_weight_units_used,
            share_value_paise=p.share_value_paise,
            payout_paise=p.payout_paise,
            status=p.status,
            calculated_at=p.calculated_at,
            finalized_at=p.finalized_at,
            created_at=p.created_at
        )
        for p in payouts
    ]

    return PayoutFinalizeResponse(
        voyage_id=voyage_id,
        status="finalized",
        total_distributed_paise=total_distributed,
        payouts=payout_responses
    )


@router.get("/{voyage_id}/payouts", response_model=List[PayoutResponse], summary="Get finalized dividend payouts for a voyage")
def list_voyage_payouts(
    voyage_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve all historical payout records for a specific voyage."""
    payouts = get_voyage_payouts(db=db, voyage_id=voyage_id)
    return [
        PayoutResponse(
            id=p.id,
            voyage_id=p.voyage_id,
            crew_member_id=p.crew_member_id,
            crew_member_name=p.crew_member.name if p.crew_member else None,
            rank_name=p.crew_member.rank.name if p.crew_member and p.crew_member.rank else None,
            share_weight_units_used=p.share_weight_units_used,
            share_value_paise=p.share_value_paise,
            payout_paise=p.payout_paise,
            status=p.status,
            calculated_at=p.calculated_at,
            finalized_at=p.finalized_at,
            created_at=p.created_at
        )
        for p in payouts
    ]


