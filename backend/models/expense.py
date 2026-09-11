"""
SQLAlchemy ORM model for Voyage Operational Expenses.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from backend.core.database import Base


class Expense(Base):
    """
    Expense model representing operational voyage costs (repairs, gunpowder, rum rations, bribes).
    Amounts are stored as exact integer paise (₹1.00 = 100 paise).
    Example: ₹8,500.00 = 850,000 paise.
    """
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    voyage_id = Column(Integer, ForeignKey("voyages.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    amount_paise = Column(Integer, nullable=False)
    date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="chk_expense_amount_paise_positive"),
    )

    # Relationships
    voyage = relationship("Voyage", back_populates="expenses")

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, voyage_id={self.voyage_id}, category='{self.category}', amount_paise={self.amount_paise})>"
