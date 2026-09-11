"""
Isolated Unit Tests for Phase 1 Database Infrastructure.
Tests SQLAlchemy engine, Base, SessionLocal, and get_db() generator dependency.
"""

import os
import sys
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import Base, get_db
from backend.core.config import DATABASE_URL


def test_sqlalchemy_import_and_version():
    """Verify SQLAlchemy 2.x is available and imports cleanly."""
    import sqlalchemy
    major_version = int(sqlalchemy.__version__.split(".")[0])
    assert major_version >= 2, f"Expected SQLAlchemy >= 2.0.0, got {sqlalchemy.__version__}"


def test_temporary_sqlite_engine_and_connection():
    """Verify SQLite engine creation and simple query execution on a temporary DB."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_db_path = Path(tmp_dir) / "test_temp.db"
        test_engine = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})

        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS is_alive"))
            row = result.fetchone()
            assert row is not None
            assert row[0] == 1

        test_engine.dispose()


def test_base_metadata_initialization():
    """Verify Declarative Base metadata can bind and create schema without errors."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_db_path = Path(tmp_dir) / "test_meta.db"
        test_engine = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})

        # Define a temporary probe model to test schema compilation
        class ProbeTable(Base):
            __tablename__ = "test_probe_table"
            id = Column(Integer, primary_key=True)
            probe_name = Column(String(50))

        Base.metadata.create_all(bind=test_engine)

        with test_engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_probe_table'"))
            table_name = res.scalar()
            assert table_name == "test_probe_table"

        # Cleanup probe table from Base metadata
        Base.metadata.remove(ProbeTable.__table__)
        test_engine.dispose()


def test_session_lifecycle_and_get_db_generator():
    """Verify get_db() dependency yields an active session and closes cleanly."""
    db_gen = get_db()
    session = next(db_gen)

    assert isinstance(session, Session)
    assert session.is_active

    # Closing session via generator continuation
    try:
        next(db_gen)
    except StopIteration:
        pass  # Expected generator exhaustion

    # Verify session closed
    assert not session.is_active or session._is_clean()


def test_sqlite_foreign_key_pragma_enforcement():
    """Verify SQLite foreign key enforcement PRAGMA is active on engine connections."""
    from backend.core.database import engine
    with engine.connect() as conn:
        res = conn.execute(text("PRAGMA foreign_keys"))
        fk_status = res.scalar()
        assert fk_status == 1, f"Expected PRAGMA foreign_keys=1, got {fk_status}"


if __name__ == "__main__":
    print("=" * 60)
    print("Running Phase 1 Database Infrastructure Tests")
    print("=" * 60)

    print("[1/5] Testing SQLAlchemy import & version...")
    test_sqlalchemy_import_and_version()
    print("  -> Passed")

    print("[2/5] Testing temporary SQLite engine & connection...")
    test_temporary_sqlite_engine_and_connection()
    print("  -> Passed")

    print("[3/5] Testing Base metadata initialization...")
    test_base_metadata_initialization()
    print("  -> Passed")

    print("[4/5] Testing Session lifecycle & get_db()...")
    test_session_lifecycle_and_get_db_generator()
    print("  -> Passed")

    print("[5/5] Testing SQLite foreign keys PRAGMA enforcement...")
    test_sqlite_foreign_key_pragma_enforcement()
    print("  -> Passed")

    print("=" * 60)
    print("All Phase 1 Database tests passed successfully! [OK]")
    print("=" * 60)
