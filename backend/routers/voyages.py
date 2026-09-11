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
from backend.schemas.voyage import VoyageCreate, VoyageUpdate, VoyageResponse
from backend.schemas.analytics import PaginatedResponse

router = APIRouter(prefix="/api/voyages", tags=["Voyages"])


def _to_voyage_response(voyage: Voyage) -> VoyageResponse:
    """Helper to convert Voyage ORM entity to VoyageResponse with calculated metrics."""
    total_expenses = sum(e.amount_paise for e in voyage.expenses) if voyage.expenses else 0
    net_profit = voyage.revenue_paise - total_expenses
    margin_bps = (net_profit * 10000 // voyage.revenue_paise) if voyage.revenue_paise > 0 else 0

    return VoyageResponse(
        id=voyage.id,
        name=voyage.name,
        date=voyage.date,
        description=voyage.description,
        revenue_paise=voyage.revenue_paise,
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

    items = [_to_voyage_response(v) for v in voyage_records]
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

    return _to_voyage_response(voyage)


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
    return _to_voyage_response(voyage)


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
    return _to_voyage_response(voyage)


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
