"""
API Router for Crew Members Management and Ledger History.
"""

from typing import List, Optional
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.core.database import get_db
from backend.models.crew import CrewMember
from backend.models.rank import Rank
from backend.models.payout import Payout
from backend.models.user import User
from backend.schemas.crew import CrewCreate, CrewUpdate, CrewResponse, CrewLedgerEntry
from backend.schemas.analytics import PaginatedResponse
from backend.dependencies.auth import require_crew_or_above, require_captain

router = APIRouter(prefix="/api/crew", tags=["Crew"])


def _to_crew_response(crew: CrewMember) -> CrewResponse:
    """Helper to map CrewMember ORM entity to CrewResponse with joined rank fields."""
    return CrewResponse(
        id=crew.id,
        name=crew.name,
        rank_id=crew.rank_id,
        rank_name=crew.rank.name if crew.rank else None,
        share_weight_units=crew.rank.share_weight_units if crew.rank else None,
        is_active=crew.is_active,
        created_at=crew.created_at,
        updated_at=crew.updated_at
    )


@router.get("", response_model=PaginatedResponse[CrewResponse], summary="List crew members with filters")
def list_crew(
    search: Optional[str] = Query(None, description="Search crew by name"),
    rank_id: Optional[int] = Query(None, description="Filter by rank ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crew_or_above)
):
    """Retrieve paginated crew members with optional search, rank, and active status filters."""
    query = db.query(CrewMember).options(joinedload(CrewMember.rank))

    if search:
        query = query.filter(CrewMember.name.ilike(f"%{search.strip()}%"))
    if rank_id is not None:
        query = query.filter(CrewMember.rank_id == rank_id)
    if is_active is not None:
        query = query.filter(CrewMember.is_active == is_active)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    crew_records = query.order_by(CrewMember.name.asc()).offset((page - 1) * page_size).limit(page_size).all()

    items = [_to_crew_response(c) for c in crew_records]
    return PaginatedResponse[CrewResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("", response_model=CrewResponse, status_code=status.HTTP_201_CREATED, summary="Enroll a new crew member")
def create_crew_member(
    payload: CrewCreate,
    db: Session = Depends(get_db),
    captain_user: User = Depends(require_captain)
):
    """Enroll a new pirate and assign a valid rank."""
    # Verify rank exists and is active
    rank = db.query(Rank).filter(Rank.id == payload.rank_id).first()
    if not rank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rank with ID {payload.rank_id} not found."
        )
    if not rank.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign an inactive rank to a crew member."
        )

    crew = CrewMember(
        name=payload.name,
        rank_id=payload.rank_id,
        is_active=payload.is_active
    )
    db.add(crew)
    db.commit()
    db.refresh(crew)

    return _to_crew_response(crew)


@router.get("/{crew_id}", response_model=CrewResponse, summary="Get crew member by ID")
def get_crew_member(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crew_or_above)
):
    """Retrieve details for an individual crew member."""
    crew = db.query(CrewMember).options(joinedload(CrewMember.rank)).filter(CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew member with ID {crew_id} not found."
        )
    return _to_crew_response(crew)


@router.put("/{crew_id}", response_model=CrewResponse, summary="Update crew member")
def update_crew_member(
    crew_id: int,
    payload: CrewUpdate,
    db: Session = Depends(get_db),
    captain_user: User = Depends(require_captain)
):
    """Update crew member details (name, rank promotion/demotion, or active status)."""
    crew = db.query(CrewMember).options(joinedload(CrewMember.rank)).filter(CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew member with ID {crew_id} not found."
        )

    if payload.name is not None:
        crew.name = payload.name

    if payload.rank_id is not None:
        rank = db.query(Rank).filter(Rank.id == payload.rank_id).first()
        if not rank:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rank with ID {payload.rank_id} not found."
            )
        crew.rank_id = payload.rank_id

    if payload.is_active is not None:
        crew.is_active = payload.is_active

    db.commit()
    db.refresh(crew)
    return _to_crew_response(crew)


@router.delete("/{crew_id}", response_model=CrewResponse, summary="Deactivate a crew member")
def delete_crew_member(
    crew_id: int,
    db: Session = Depends(get_db),
    captain_user: User = Depends(require_captain)
):
    """
    Soft-deactivates a crew member (is_active=False).
    Physical record deletion is prevented so historical dividend logs remain historically accurate.
    """
    crew = db.query(CrewMember).options(joinedload(CrewMember.rank)).filter(CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew member with ID {crew_id} not found."
        )

    crew.is_active = False
    db.commit()
    db.refresh(crew)
    return _to_crew_response(crew)


@router.get("/{crew_id}/ledger", response_model=List[CrewLedgerEntry], summary="Get individual pirate ledger history")
def get_crew_ledger(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crew_or_above)
):
    """Retrieve the complete chronological dividend payout history for a crew member."""
    crew = db.query(CrewMember).options(joinedload(CrewMember.rank)).filter(CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew member with ID {crew_id} not found."
        )

    payouts = (
        db.query(Payout)
        .options(joinedload(Payout.voyage), joinedload(Payout.crew_member))
        .filter(Payout.crew_member_id == crew_id)
        .order_by(Payout.calculated_at.desc())
        .all()
    )

    ledger_entries = []
    for p in payouts:
        ledger_entries.append(
            CrewLedgerEntry(
                id=p.id,
                voyage_id=p.voyage_id,
                voyage_name=p.voyage.name if p.voyage else "Unknown Voyage",
                crew_member_id=p.crew_member_id,
                crew_member_name=crew.name,
                rank_name=crew.rank.name if crew.rank else "Unknown Rank",
                share_weight_units_used=p.share_weight_units_used,
                share_value_paise=p.share_value_paise,
                payout_paise=p.payout_paise,
                status=p.status,
                calculated_at=p.calculated_at,
                finalized_at=p.finalized_at
            )
        )

    return ledger_entries
