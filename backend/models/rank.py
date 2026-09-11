"""
SQLAlchemy ORM model for Pirate Ranks and configurable integer share weights.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from backend.core.database import Base


class Rank(Base):
    """
    Rank model representing hierarchical pirate positions.
    Share weights are stored as exact integer share units (e.g. 100 units = 1.0x share).
    Examples:
        Captain (2.0x)       = 200 share units
        First Mate (1.5x)    = 150 share units
        Able Seaman (1.0x)   = 100 share units
        Powder Monkey (0.5x) = 50 share units
    """
    __tablename__ = "ranks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    share_weight_units = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("share_weight_units > 0", name="chk_rank_share_weight_units_positive"),
    )

    # Relationships
    crew_members = relationship("CrewMember", back_populates="rank", passive_deletes="all")

    def __repr__(self) -> str:
        return f"<Rank(id={self.id}, name='{self.name}', share_weight_units={self.share_weight_units})>"
