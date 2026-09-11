"""
Payout & Dividend Distribution Service for Captain's Treasure Ledger.
Implements exact integer dividend distribution, deterministic remainder allocation,
historical share weight snapshotting, idempotency protections, and crew balance tracking.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, UTC
from fastapi import HTTPException, Header, status
from sqlalchemy.orm import Session, joinedload

from backend.models.voyage import Voyage
from backend.models.crew import CrewMember
from backend.models.rank import Rank
from backend.models.payout import Payout
from backend.models.transaction import TransactionLog
from backend.services.financial_service import get_voyage_financial_summary


def calculate_integer_payout_distribution(
    distributable_profit_paise: int,
    eligible_crew: List[CrewMember]
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Core mathematical dividend distribution algorithm.
    Guarantees zero paise loss using exact integer math and deterministic remainder allocation.

    Formula:
      base_payout = (distributable_profit_paise * share_weight_units) // total_share_weight_units
      fractional_rem = (distributable_profit_paise * share_weight_units) % total_share_weight_units
      remaining_paise = distributable_profit_paise - sum(base_payouts)

    Deterministic Remainder Strategy:
      Sort members by highest fractional remainder first; tie-breaker: crew_member_id ascending.
      Allocate 1 paise to the top `remaining_paise` members.

    Invariant:
      SUM(payout_paise) == distributable_profit_paise (whenever distributable_profit_paise > 0)
    """
    if distributable_profit_paise <= 0:
        return [], 0, 0

    if not eligible_crew:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active crew members available for dividend division."
        )

    # Compute total share weight
    total_share_units = sum(c.rank.share_weight_units for c in eligible_crew if c.rank)
    if total_share_units <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total crew share weight units must be greater than zero."
        )

    share_value_paise = distributable_profit_paise // total_share_units

    # Step 1 & 2: Base payouts and fractional remainders
    temp_allocations = []
    for crew in eligible_crew:
        weight = crew.rank.share_weight_units
        numerator = distributable_profit_paise * weight
        base_payout = numerator // total_share_units
        fractional_rem = numerator % total_share_units

        temp_allocations.append({
            "crew_member_id": crew.id,
            "crew_member_name": crew.name,
            "rank_name": crew.rank.name if crew.rank else "Unknown",
            "share_weight_units": weight,
            "base_payout": base_payout,
            "fractional_rem": fractional_rem,
            "extra_paise": 0
        })

    # Step 3: Compute remaining paise
    sum_base = sum(item["base_payout"] for item in temp_allocations)
    remaining_paise = distributable_profit_paise - sum_base

    # Step 4: Deterministic remainder allocation (sort by highest fractional remainder, then crew_id ascending)
    sorted_indices = sorted(
        range(len(temp_allocations)),
        key=lambda i: (-temp_allocations[i]["fractional_rem"], temp_allocations[i]["crew_member_id"])
    )

    for i in range(remaining_paise):
        idx = sorted_indices[i % len(sorted_indices)]
        temp_allocations[idx]["extra_paise"] += 1

    # Step 5: Finalize item amounts and assert strict invariant
    final_items = []
    total_payout = 0
    for item in temp_allocations:
        final_payout = item["base_payout"] + item["extra_paise"]
        total_payout += final_payout
        final_items.append({
            "crew_member_id": item["crew_member_id"],
            "crew_member_name": item["crew_member_name"],
            "rank_name": item["rank_name"],
            "share_weight_units": item["share_weight_units"],
            "payout_paise": final_payout
        })

    assert total_payout == distributable_profit_paise, (
        f"CRITICAL FINANCIAL INVARIANT VIOLATION: Sum of payouts ({total_payout}) "
        f"does not equal distributable profit ({distributable_profit_paise})"
    )

    return final_items, total_share_units, share_value_paise


def get_eligible_active_crew(db: Session) -> List[CrewMember]:
    """Retrieve all active crew members assigned to active ranks."""
    return (
        db.query(CrewMember)
        .options(joinedload(CrewMember.rank))
        .filter(CrewMember.is_active == True)
        .all()
    )


def preview_voyage_payouts(db: Session, voyage_id: int) -> Dict[str, Any]:
    """
    Generate an uncommitted, transparent dividend preview for a voyage.
    Does NOT modify the database or create permanent payout records.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    fin_summary = get_voyage_financial_summary(db=db, voyage_id=voyage_id)
    distributable_profit = fin_summary["distributable_profit_paise"]

    if distributable_profit <= 0:
        return {
            "voyage_id": voyage.id,
            "voyage_name": voyage.name,
            "revenue_paise": fin_summary["revenue_paise"],
            "total_expenses_paise": fin_summary["expenses_paise"],
            "net_profit_paise": fin_summary["net_profit_paise"],
            "distributable_profit_paise": 0,
            "total_share_units": 0,
            "share_value_value_paise": 0,
            "share_value_paise": 0,
            "remainder_paise": 0,
            "items": []
        }

    eligible_crew = get_eligible_active_crew(db)
    items, total_shares, share_val = calculate_integer_payout_distribution(
        distributable_profit_paise=distributable_profit,
        eligible_crew=eligible_crew
    )

    return {
        "voyage_id": voyage.id,
        "voyage_name": voyage.name,
        "revenue_paise": fin_summary["revenue_paise"],
        "total_expenses_paise": fin_summary["expenses_paise"],
        "net_profit_paise": fin_summary["net_profit_paise"],
        "distributable_profit_paise": distributable_profit,
        "total_share_units": total_shares,
        "share_value_paise": share_val,
        "remainder_paise": 0,
        "items": items
    }


def finalize_voyage_payouts(
    db: Session,
    voyage_id: int,
    user_role: Optional[str] = None
) -> Tuple[Voyage, List[Payout]]:
    """
    Atomically finalize and commit immutable dividend payouts for a completed voyage.
    Enforces authorization, lifecycle state, idempotency, and zero-loss invariant.
    """
    # 1. Authorization check: CREW cannot finalize payouts
    if user_role and user_role.lower() == "crew":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Crew members are not authorized to finalize dividend payouts. Captain or Admin authorization required."
        )

    # 2. Voyage existence and completion check
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    if voyage.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize payouts for voyage with status '{voyage.status}'. Payouts require a 'completed' voyage."
        )

    # 3. Idempotency guard: Prevent duplicate payout finalization
    existing_payouts_count = db.query(Payout).filter(Payout.voyage_id == voyage_id).count()
    if existing_payouts_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dividend payouts have already been finalized for voyage '{voyage.name}' (ID: {voyage_id})."
        )

    # 4. Financial verification
    fin_summary = get_voyage_financial_summary(db=db, voyage_id=voyage_id)
    distributable_profit = fin_summary["distributable_profit_paise"]
    if distributable_profit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize payouts: voyage '{voyage.name}' has zero or negative distributable profit ({distributable_profit} paise)."
        )

    # 5. Active crew retrieval and exact distribution
    eligible_crew = get_eligible_active_crew(db)
    items, total_shares, share_val = calculate_integer_payout_distribution(
        distributable_profit_paise=distributable_profit,
        eligible_crew=eligible_crew
    )

    # 6. Atomic database creation
    now = datetime.now(UTC)
    created_payouts = []
    try:
        for item in items:
            payout = Payout(
                voyage_id=voyage_id,
                crew_member_id=item["crew_member_id"],
                share_weight_units_used=item["share_weight_units"],
                share_value_paise=share_val,
                payout_paise=item["payout_paise"],
                status="finalized",
                calculated_at=now,
                finalized_at=now,
                created_at=now
            )
            db.add(payout)
            created_payouts.append(payout)

        # Post audit transaction log entry for the dividend disbursement
        tx_desc = f"Dividend payout finalized for voyage '{voyage.name}' across {len(created_payouts)} crew members"
        tx = TransactionLog(
            voyage_id=voyage_id,
            transaction_type="DEBIT",
            amount_paise=distributable_profit,
            description=tx_desc,
            reference_type="voyage_payout",
            reference_id=voyage_id,
            timestamp=now
        )
        db.add(tx)

        db.commit()

        for p in created_payouts:
            db.refresh(p)

        return voyage, created_payouts
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Atomic payout finalization failed: {str(e)}"
        )


def get_voyage_payouts(db: Session, voyage_id: int) -> List[Payout]:
    """Retrieve all historical payout records for a specific voyage."""
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    return (
        db.query(Payout)
        .options(joinedload(Payout.crew_member), joinedload(Payout.voyage))
        .filter(Payout.voyage_id == voyage_id)
        .order_by(Payout.payout_paise.desc())
        .all()
    )


def get_crew_payout_history(db: Session, crew_member_id: int) -> List[Payout]:
    """Retrieve complete chronological payout history for an individual crew member."""
    crew = db.query(CrewMember).filter(CrewMember.id == crew_member_id).first()
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew member with ID {crew_member_id} not found."
        )

    return (
        db.query(Payout)
        .options(joinedload(Payout.voyage), joinedload(Payout.crew_member))
        .filter(Payout.crew_member_id == crew_member_id)
        .order_by(Payout.calculated_at.desc())
        .all()
    )


def get_crew_cumulative_balance(db: Session, crew_member_id: int) -> Dict[str, Any]:
    """Calculate cumulative running balance in integer paise from historical finalized payout records."""
    crew = db.query(CrewMember).options(joinedload(CrewMember.rank)).filter(CrewMember.id == crew_member_id).first()
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew member with ID {crew_member_id} not found."
        )

    payouts = db.query(Payout).filter(Payout.crew_member_id == crew_member_id).all()
    running_balance = sum(p.payout_paise for p in payouts if p.status in ["finalized", "paid", "calculated"])

    return {
        "crew_member_id": crew.id,
        "crew_member_name": crew.name,
        "rank_name": crew.rank.name if crew.rank else "Unknown",
        "running_balance_paise": running_balance
    }
