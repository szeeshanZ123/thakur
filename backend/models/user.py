"""
SQLAlchemy ORM model for System Users and Role-Based Access Control.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from backend.core.database import Base


class User(Base):
    """
    User model representing authenticated users of Captain's Treasure Ledger.
    Supports role-based authorization (ADMIN, CAPTAIN, CREW) and soft deactivation.
    Passwords are never stored in plaintext.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="CREW", index=True)  # ADMIN, CAPTAIN, CREW
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{self.role}', is_active={self.is_active})>"
