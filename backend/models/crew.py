"""
SQLAlchemy ORM model for Crew Members.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.core.database import Base


class CrewMember(Base):
    """
    CrewMember model representing individual pirates aboard the vessel.
    Supports soft deactivation (is_active = False) so historical payout records are never lost.
    """
    __tablename__ = "crew_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    rank_id = Column(Integer, ForeignKey("ranks.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    rank = relationship("Rank", back_populates="crew_members")
    payouts = relationship("Payout", back_populates="crew_member", passive_deletes="all")

    def __repr__(self) -> str:
        return f"<CrewMember(id={self.id}, name='{self.name}', rank_id={self.rank_id}, is_active={self.is_active})>"
