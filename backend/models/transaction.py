"""
SQLAlchemy ORM model for Immutable Append-Only Treasury Transaction Log.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from backend.core.database import Base


class TransactionLog(Base):
    """
    TransactionLog represents an immutable, append-only ledger entry.
    All financial events (revenue credits, expense debits, reversals, corrections) are permanently logged.
    Amounts are stored as exact positive integer paise; the transaction_type determines the financial direction.
    """
    __tablename__ = "transaction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    voyage_id = Column(Integer, ForeignKey("voyages.id", ondelete="RESTRICT"), nullable=True, index=True)
    transaction_type = Column(String(20), nullable=False, index=True)  # CREDIT, DEBIT, REVERSAL, CORRECTION
    amount_paise = Column(Integer, nullable=False)
    description = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    reference_type = Column(String(50), nullable=True)  # e.g., 'voyage_revenue', 'expense', 'payout'
    reference_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="chk_transaction_amount_paise_positive"),
    )

    # Relationships
    voyage = relationship("Voyage", back_populates="transaction_logs")

    def __repr__(self) -> str:
        return (
            f"<TransactionLog(id={self.id}, type='{self.transaction_type}', "
            f"amount_paise={self.amount_paise}, voyage_id={self.voyage_id})>"
        )
