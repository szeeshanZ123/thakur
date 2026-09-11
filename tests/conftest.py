"""
Session-scoped test infrastructure shared by all test modules.

Provides:
  - ``test_engine``  : in-memory SQLite engine (StaticPool) isolated per session
  - ``test_db``      : factory for direct DB access in tests
  - ``client``       : FastAPI TestClient with get_db overridden to use test engine
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ALL models so every table is registered in Base.metadata
import backend.models  # noqa: F401

from backend.core.database import Base, get_db
from backend.main import app


# Single shared in-memory SQLite engine for all tests
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def _install_db_override():
    """
    Install the test DB override BEFORE any test runs.
    This must happen before the TestClient is created so the startup
    event (init_db) fires against the production engine while all
    subsequent requests use our test engine.
    """
    Base.metadata.create_all(bind=_engine)
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="session")
def client(_install_db_override):
    """FastAPI TestClient shared across the whole test session."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="session")
def test_session():
    """Direct SQLAlchemy session for seeding/verifying data in tests."""
    return _Session
