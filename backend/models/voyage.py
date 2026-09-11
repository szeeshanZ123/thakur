"""
SQLAlchemy ORM model for Expeditions and Voyages.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from backend.core.database import Base


class Voyage(Base):
    """
    Voyage model representing maritime expeditions and raids.
    Gross loot revenue is stored as exact integer paise (₹1.00 = 100 paise).
    Example: ₹50,000.00 gross loot = 5,000,000 paise.
    """
    __tablename__ = "voyages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    description = Column(Text, nullable=True)
    revenue_paise = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="planned", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("revenue_paise >= 0", name="chk_voyage_revenue_paise_non_negative"),
    )

    # Relationships
    expenses = relationship("Expense", back_populates="voyage", cascade="all, delete-orphan")
    transaction_logs = relationship("TransactionLog", back_populates="voyage", passive_deletes="all")
    payouts = relationship("Payout", back_populates="voyage", passive_deletes="all")

    def __repr__(self) -> str:
        return f"<Voyage(id={self.id}, name='{self.name}', revenue_paise={self.revenue_paise}, status='{self.status}')>"
