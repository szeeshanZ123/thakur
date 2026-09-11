"""
API Router for Pirate Ranks Management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.core.database import get_db
from backend.models.rank import Rank
from backend.models.crew import CrewMember
from backend.schemas.rank import RankCreate, RankUpdate, RankResponse

router = APIRouter(prefix="/api/ranks", tags=["Ranks"])


@router.get("", response_model=List[RankResponse], summary="List all pirate ranks")
def list_ranks(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    """Retrieve all configurable pirate ranks and their integer share weights."""
    query = db.query(Rank)
    if is_active is not None:
        query = query.filter(Rank.is_active == is_active)
    return query.order_by(Rank.share_weight_units.desc()).all()


@router.post("", response_model=RankResponse, status_code=status.HTTP_201_CREATED, summary="Create a new pirate rank")
def create_rank(
    payload: RankCreate,
    db: Session = Depends(get_db)
):
    """Create a new rank with configurable positive integer share units (e.g., 200 for 2.0x)."""
    # Check for duplicate rank name
    existing = db.query(Rank).filter(Rank.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rank with name '{payload.name}' already exists."
        )

    rank = Rank(
        name=payload.name,
        share_weight_units=payload.share_weight_units,
        is_active=payload.is_active
    )
    db.add(rank)
    try:
        db.commit()
        db.refresh(rank)
        return rank
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rank creation failed due to uniqueness constraint."
        )


@router.get("/{rank_id}", response_model=RankResponse, summary="Get rank by ID")
def get_rank(
    rank_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details for a specific pirate rank."""
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rank with ID {rank_id} not found."
        )
    return rank


@router.put("/{rank_id}", response_model=RankResponse, summary="Update a pirate rank")
def update_rank(
    rank_id: int,
    payload: RankUpdate,
    db: Session = Depends(get_db)
):
    """
    Update rank metadata or share weight units.
    Note: Changing share_weight_units applies to FUTURE payout divisions only; past payouts remain immutable.
    """
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rank with ID {rank_id} not found."
        )

    if payload.name is not None and payload.name != rank.name:
        existing = db.query(Rank).filter(Rank.name == payload.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rank with name '{payload.name}' already exists."
            )
        rank.name = payload.name

    if payload.share_weight_units is not None:
        rank.share_weight_units = payload.share_weight_units

    if payload.is_active is not None:
        rank.is_active = payload.is_active

    db.commit()
    db.refresh(rank)
    return rank


@router.delete("/{rank_id}", response_model=RankResponse, summary="Delete or deactivate a pirate rank")
def delete_rank(
    rank_id: int,
    db: Session = Depends(get_db)
):
    """
    Safely deactivate or remove a rank.
    If crew members are currently assigned, soft-deactivates (is_active=False) to protect relational integrity.
    """
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rank with ID {rank_id} not found."
        )

    # Check if crew members are assigned to this rank
    crew_count = db.query(CrewMember).filter(CrewMember.rank_id == rank_id).count()
    if crew_count > 0:
        # Soft deactivate
        rank.is_active = False
        db.commit()
        db.refresh(rank)
        return rank

    # Safe to delete if no crew references exist
    db.delete(rank)
    db.commit()
    return rank
