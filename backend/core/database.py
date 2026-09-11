"""
SQLAlchemy database engine, declarative Base, and session management.
"""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from backend.core.config import DATABASE_URL


class Base(DeclarativeBase):
    """
    Declarative Base class for all SQLAlchemy ORM models.
    Architectural Standard:
    - All monetary amounts stored as exact integer minor units (e.g. cents/paise, 100 minor units = 1 standard unit).
    - All share weights stored as exact integer units.
    - Zero floating-point representation in financial records.
    """
    pass


# SQLite-specific connection arguments
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

# Enforce foreign key constraints on SQLite connections
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Closes the session automatically upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize all registered ORM models in the database schema.
    """
    Base.metadata.create_all(bind=engine)
