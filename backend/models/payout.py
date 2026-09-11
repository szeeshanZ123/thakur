"""
SQLAlchemy ORM model for Individual Pirate Voyage Payouts.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from backend.core.database import Base


class Payout(Base):
    """
    Payout model storing individual dividend allocations per voyage and crew member.
    Captures exact historical snapshots:
    - share_weight_units_used: snapshot of crew rank weight at calculation time.
    - share_value_paise: value per single share unit in integer paise.
    - payout_paise: total dividend paid to pirate in integer paise.
    """
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    voyage_id = Column(Integer, ForeignKey("voyages.id", ondelete="RESTRICT"), nullable=False, index=True)
    crew_member_id = Column(Integer, ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    share_weight_units_used = Column(Integer, nullable=False)
    share_value_paise = Column(Integer, nullable=False)
    payout_paise = Column(Integer, nullable=False)
    status = Column(String(20), default="calculated", nullable=False, index=True)  # calculated, approved, paid
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    finalized_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("share_weight_units_used > 0", name="chk_payout_share_weight_units_positive"),
        CheckConstraint("share_value_paise >= 0", name="chk_payout_share_value_paise_non_negative"),
        CheckConstraint("payout_paise >= 0", name="chk_payout_payout_paise_non_negative"),
    )

    # Relationships
    voyage = relationship("Voyage", back_populates="payouts")
    crew_member = relationship("CrewMember", back_populates="payouts")

    def __repr__(self) -> str:
        return (
            f"<Payout(id={self.id}, voyage_id={self.voyage_id}, crew_id={self.crew_member_id}, "
            f"payout_paise={self.payout_paise}, status='{self.status}')>"
        )
