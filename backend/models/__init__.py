"""
SQLAlchemy ORM models package for Captain's Treasure Ledger.
Models (Rank, CrewMember, Voyage, Expense, Payout, TransactionLog) will be registered in Phase 2.
All monetary entities adhere to zero-loss integer minor unit arithmetic (cents/paise) and integer share units.
"""

from backend.core.database import Base

__all__ = ["Base"]
