"""
Unit Tests for Phase 2 Database ORM Models.
Tests all six models, zero-loss integer fields, relationships, foreign keys,
historical payout snapshot preservation, and append-only audit logging.
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
try:
    import pytest
    fixture = pytest.fixture
    raises = pytest.raises
except ImportError:
    def fixture(fn):
        return fn

    class raises:
        def __init__(self, expected_exc):
            self.expected_exc = expected_exc

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            assert exc_type is not None and issubclass(exc_type, self.expected_exc), (
                f"Expected exception {self.expected_exc}, but got {exc_type}"
            )
            return True
from sqlalchemy import create_engine, text, event, Integer, Float
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import Base
from backend.models.rank import Rank
from backend.models.crew import CrewMember
from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog
from backend.models.payout import Payout


@fixture
def test_db_session():
    """Create an isolated temporary SQLite database and session with FK enforcement."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_db_path = Path(tmp_dir) / "test_models.db"
        test_engine = create_engine(
            f"sqlite:///{temp_db_path}",
            connect_args={"check_same_thread": False}
        )

        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(bind=test_engine)
        SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = SessionTest()

        try:
            yield session
        finally:
            session.close()
            test_engine.dispose()


def test_no_float_monetary_or_share_fields():
    """Verify that NO financial or share weight fields use Float / Double."""
    models_to_check = [
        (Rank, ["share_weight_units"]),
        (Voyage, ["revenue_paise"]),
        (Expense, ["amount_paise"]),
        (TransactionLog, ["amount_paise"]),
        (Payout, ["share_weight_units_used", "share_value_paise", "payout_paise"]),
    ]

    for model_cls, fields in models_to_check:
        for field_name in fields:
            col = getattr(model_cls, field_name).property.columns[0]
            assert isinstance(col.type, Integer), f"{model_cls.__name__}.{field_name} must be Integer, got {col.type}"
            assert not isinstance(col.type, Float), f"{model_cls.__name__}.{field_name} cannot be Float"


def test_rank_creation_and_crew_relationship(test_db_session):
    """Verify Rank creation with integer share units and CrewMember relationship."""
    session = test_db_session

    # 1. Create Rank
    captain_rank = Rank(name="Captain", share_weight_units=200, is_active=True)
    session.add(captain_rank)
    session.commit()
    session.refresh(captain_rank)

    assert captain_rank.id is not None
    assert captain_rank.share_weight_units == 200

    # 2. Create CrewMember referencing Rank
    pirate = CrewMember(name="Blackbeard", rank_id=captain_rank.id, is_active=True)
    session.add(pirate)
    session.commit()
    session.refresh(pirate)

    assert pirate.id is not None
    assert pirate.rank.name == "Captain"
    assert len(captain_rank.crew_members) == 1
    assert captain_rank.crew_members[0].name == "Blackbeard"


def test_voyage_expenses_and_transactions(test_db_session):
    """Verify Voyage with integer revenue, Expense with integer amount, and TransactionLog."""
    session = test_db_session

    # 1. Create Voyage (e.g. ₹50,000 gross revenue = 5,000,000 paise)
    voyage = Voyage(
        name="Spanish Main Expedition",
        date=datetime.utcnow(),
        description="Raid on merchant convoy",
        revenue_paise=5000000,
        status="completed"
    )
    session.add(voyage)
    session.commit()
    session.refresh(voyage)

    assert voyage.id is not None
    assert voyage.revenue_paise == 5000000

    # 2. Create Expense (e.g. ₹8,500 repair expense = 850,000 paise)
    expense = Expense(
        voyage_id=voyage.id,
        category="Ship Repair",
        amount_paise=850000,
        description="Hull patching and mast repairs"
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)

    assert expense.id is not None
    assert expense.amount_paise == 850000
    assert expense.voyage.name == "Spanish Main Expedition"
    assert len(voyage.expenses) == 1

    # 3. Create TransactionLog (e.g. Credit of ₹50,000 = 5,000,000 paise)
    tx_credit = TransactionLog(
        voyage_id=voyage.id,
        transaction_type="CREDIT",
        amount_paise=5000000,
        description="Gross loot from Spanish Main Expedition",
        reference_type="voyage_revenue",
        reference_id=voyage.id
    )
    session.add(tx_credit)
    session.commit()
    session.refresh(tx_credit)

    assert tx_credit.id is not None
    assert tx_credit.amount_paise == 5000000
    assert tx_credit.transaction_type == "CREDIT"
    assert len(voyage.transaction_logs) == 1


def test_payout_creation_and_historical_snapshot(test_db_session):
    """Verify historical payout snapshot is preserved even when rank share weight changes."""
    session = test_db_session

    # 1. Setup Rank (Captain = 200 units)
    rank = Rank(name="Captain", share_weight_units=200)
    session.add(rank)
    session.commit()

    # 2. Setup CrewMember
    crew = CrewMember(name="Jack Sparrow", rank_id=rank.id)
    session.add(crew)

    # 3. Setup Voyage
    voyage = Voyage(name="Tortuga Run", date=datetime.utcnow(), revenue_paise=1000000)
    session.add(voyage)
    session.commit()

    # 4. Create Payout record snapshotting share_weight_units_used = 200
    payout = Payout(
        voyage_id=voyage.id,
        crew_member_id=crew.id,
        share_weight_units_used=200,
        share_value_paise=25000,  # ₹250 per share unit
        payout_paise=5000000,     # ₹50,000 total dividend
        status="paid",
        calculated_at=datetime.utcnow(),
        finalized_at=datetime.utcnow()
    )
    session.add(payout)
    session.commit()
    session.refresh(payout)

    assert payout.share_weight_units_used == 200
    assert payout.payout_paise == 5000000

    # 5. Later, rank share weight changes to 250 units
    rank.share_weight_units = 250
    session.commit()
    session.refresh(rank)
    assert rank.share_weight_units == 250

    # 6. Verify historical payout record STILL contains 200 units
    session.refresh(payout)
    assert payout.share_weight_units_used == 200, "Historical payout share weight must remain unchanged!"
    assert payout.payout_paise == 5000000


def test_foreign_key_enforcement_rejects_invalid_references(test_db_session):
    """Verify that invalid foreign key references raise IntegrityError with SQLite FK enforcement."""
    session = test_db_session

    # Invalid rank_id = 9999
    invalid_crew = CrewMember(name="Ghost Pirate", rank_id=9999)
    session.add(invalid_crew)

    with raises(IntegrityError):
        session.commit()

    session.rollback()


def test_transaction_log_append_only_pattern(test_db_session):
    """Verify that TransactionLog records are never updated in place; corrections are append-only."""
    session = test_db_session

    voyage = Voyage(name="Bahamas Run", date=datetime.utcnow(), revenue_paise=2000000)
    session.add(voyage)
    session.commit()

    # 1. Original transaction
    tx_original = TransactionLog(
        voyage_id=voyage.id,
        transaction_type="CREDIT",
        amount_paise=2000000,
        description="Initial estimated cargo revenue",
        reference_type="voyage_revenue",
        reference_id=voyage.id
    )
    session.add(tx_original)
    session.commit()
    original_id = tx_original.id

    # 2. Correction required: Do NOT edit original. Append a REVERSAL transaction.
    tx_reversal = TransactionLog(
        voyage_id=voyage.id,
        transaction_type="REVERSAL",
        amount_paise=500000,
        description="Reversal for damaged cargo adjustment",
        reference_type="transaction_correction",
        reference_id=original_id
    )
    session.add(tx_reversal)
    session.commit()

    # 3. Verify original record remained intact and unchanged
    fetched_original = session.query(TransactionLog).filter_by(id=original_id).one()
    assert fetched_original.amount_paise == 2000000
    assert fetched_original.transaction_type == "CREDIT"

    # 4. Total transactions logged for voyage = 2
    all_logs = session.query(TransactionLog).filter_by(voyage_id=voyage.id).all()
    assert len(all_logs) == 2


def run_with_fresh_session(test_func):
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_db_path = Path(temp_dir) / "test_isolated.db"
        runner_engine = create_engine(f"sqlite:///{tmp_db_path}", connect_args={"check_same_thread": False})

        @event.listens_for(runner_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(bind=runner_engine)
        SessionRunner = sessionmaker(autocommit=False, autoflush=False, bind=runner_engine)
        s = SessionRunner()

        try:
            test_func(s)
        finally:
            s.close()
            runner_engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Running Phase 2 Database ORM Models Test Suite")
    print("=" * 60)

    print("[1/6] Testing No Float Monetary or Share Fields...")
    test_no_float_monetary_or_share_fields()
    print("  -> Passed")

    print("[2/6] Testing Rank & CrewMember Relationships...")
    run_with_fresh_session(test_rank_creation_and_crew_relationship)
    print("  -> Passed")

    print("[3/6] Testing Voyage, Expense & TransactionLog...")
    run_with_fresh_session(test_voyage_expenses_and_transactions)
    print("  -> Passed")

    print("[4/6] Testing Payout & Historical Snapshot Reproducibility...")
    run_with_fresh_session(test_payout_creation_and_historical_snapshot)
    print("  -> Passed")

    print("[5/6] Testing Foreign Key Enforcement (IntegrityError)...")
    run_with_fresh_session(test_foreign_key_enforcement_rejects_invalid_references)
    print("  -> Passed")

    print("[6/6] Testing Append-Only TransactionLog Pattern...")
    run_with_fresh_session(test_transaction_log_append_only_pattern)
    print("  -> Passed")

    print("=" * 60)
    print("All 6 Phase 2 ORM Model test suites passed successfully! [OK]")
    print("=" * 60)
