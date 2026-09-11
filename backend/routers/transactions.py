"""
API Router for Read-Only Immutable Treasury Transaction Logs.
Strictly read-only: No PUT or DELETE endpoints exist for transaction logs.
"""

from typing import List, Optional
from datetime import datetime
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.transaction import TransactionLog
from backend.models.voyage import Voyage
from backend.schemas.transaction import TransactionResponse
from backend.schemas.analytics import PaginatedResponse

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=PaginatedResponse[TransactionResponse], summary="List immutable transaction history")
def list_transactions(
    voyage_id: Optional[int] = Query(None, description="Filter by voyage ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by type (CREDIT, DEBIT, REVERSAL, CORRECTION)"),
    date_from: Optional[datetime] = Query(None, description="Filter timestamp on or after"),
    date_to: Optional[datetime] = Query(None, description="Filter timestamp on or before"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated immutable transaction history ordered chronologically by timestamp descending."""
    query = db.query(TransactionLog)

    if voyage_id is not None:
        query = query.filter(TransactionLog.voyage_id == voyage_id)
    if transaction_type:
        query = query.filter(TransactionLog.transaction_type == transaction_type.upper())
    if date_from:
        query = query.filter(TransactionLog.timestamp >= date_from)
    if date_to:
        query = query.filter(TransactionLog.timestamp <= date_to)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    transactions = query.order_by(TransactionLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse[TransactionResponse](
        items=transactions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{transaction_id}", response_model=TransactionResponse, summary="Get transaction by ID")
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details for a single immutable transaction record."""
    tx = db.query(TransactionLog).filter(TransactionLog.id == transaction_id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found."
        )
    return tx


@router.get("/voyage/{voyage_id}", response_model=List[TransactionResponse], summary="Get chronological audit timeline for a voyage")
def get_voyage_transactions(
    voyage_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve all audit transactions for a specific voyage sorted by timestamp ascending
    for reconstructing the chronological financial timeline.
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
