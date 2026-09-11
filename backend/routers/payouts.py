"""
API Router for Read-Only Historical Dividend Payout Records.
Finalized payout records are strictly immutable.
"""

from typing import List, Optional
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.core.database import get_db
from backend.models.payout import Payout
from backend.models.voyage import Voyage
from backend.models.crew import CrewMember
from backend.schemas.payout import PayoutResponse
from backend.schemas.analytics import PaginatedResponse

router = APIRouter(prefix="/api/payouts", tags=["Payouts"])


def _to_payout_response(p: Payout) -> PayoutResponse:
    return PayoutResponse(
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


@router.get("", response_model=PaginatedResponse[PayoutResponse], summary="List historical dividend payouts with filters")
def list_payouts(
    voyage_id: Optional[int] = Query(None, description="Filter by voyage ID"),
    crew_member_id: Optional[int] = Query(None, description="Filter by crew member ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (calculated, finalized, paid)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated immutable dividend payout history."""
    query = db.query(Payout).options(joinedload(Payout.crew_member).joinedload(CrewMember.rank), joinedload(Payout.voyage))

    if voyage_id is not None:
        query = query.filter(Payout.voyage_id == voyage_id)
    if crew_member_id is not None:
        query = query.filter(Payout.crew_member_id == crew_member_id)
    if status_filter:
        query = query.filter(Payout.status == status_filter)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    payouts = query.order_by(Payout.calculated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = [_to_payout_response(p) for p in payouts]
    return PaginatedResponse[PayoutResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{payout_id}", response_model=PayoutResponse, summary="Get payout record by ID")
def get_payout(
    payout_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details for a single immutable payout record."""
    p = (
        db.query(Payout)
        .options(joinedload(Payout.crew_member).joinedload(CrewMember.rank), joinedload(Payout.voyage))
        .filter(Payout.id == payout_id)
        .first()
    )
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payout with ID {payout_id} not found."
        )
    return _to_payout_response(p)
