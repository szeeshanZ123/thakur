"""
Unit Tests for Phase 3 Pydantic Schemas and API Data Contracts.
Tests schema validation, rejection of floating-point values for money/shares,
ORM object serialization, and analytics contract structures.
"""

import os
import sys
from datetime import datetime
from pydantic import ValidationError

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

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.schemas.rank import RankCreate, RankUpdate, RankResponse
from backend.schemas.crew import CrewCreate, CrewUpdate, CrewResponse, CrewLedgerEntry
from backend.schemas.voyage import VoyageCreate, VoyageUpdate, VoyageResponse
from backend.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from backend.schemas.transaction import TransactionResponse, TransactionCreateInternal
from backend.schemas.payout import PayoutResponse, PayoutPreview, PayoutPreviewItem, PayoutFinalizeResponse
from backend.schemas.analytics import (
    DashboardKPIs,
    RevenueExpensePoint,
    RevenueExpenseResponse,
    ExpenseBreakdownItem,
    ExpenseBreakdownResponse,
    ProfitAnalyticsResponse,
    CrewEarningsItem,
    CrewEarningsResponse,
)
from backend.models.rank import Rank
from backend.models.voyage import Voyage
from backend.models.expense import Expense


# --- 1. Rank Schema Tests ---

def test_valid_rank_create():
    schema = RankCreate(name="Quartermaster", share_weight_units=150, is_active=True)
    assert schema.name == "Quartermaster"
    assert schema.share_weight_units == 150
    assert schema.is_active is True


def test_invalid_rank_share_weight_units():
    # Zero share weight rejected
    with raises(ValidationError):
        RankCreate(name="Cabin Boy", share_weight_units=0)

    # Negative share weight rejected
    with raises(ValidationError):
        RankCreate(name="Cabin Boy", share_weight_units=-50)

    # Float share weight rejected (strict integer requirement)
    with raises(ValidationError):
        RankCreate(name="Captain", share_weight_units=2.5)


def test_invalid_empty_rank_name():
    with raises(ValidationError):
        RankCreate(name="   ", share_weight_units=100)


# --- 2. Crew Schema Tests ---

def test_valid_crew_create():
    schema = CrewCreate(name="Long John Silver", rank_id=1, is_active=True)
    assert schema.name == "Long John Silver"
    assert schema.rank_id == 1


def test_invalid_crew_create_rank_id():
    with raises(ValidationError):
        CrewCreate(name="Pirate", rank_id=0)

    with raises(ValidationError):
        CrewCreate(name="Pirate", rank_id=-1)


# --- 3. Voyage Schema Tests ---

def test_valid_voyage_create():
    schema = VoyageCreate(
        name="Raid on Port Royal",
        date=datetime.utcnow(),
        description="Treasure galleon attack",
        revenue_paise=5000000,
        status="completed"
    )
    assert schema.name == "Raid on Port Royal"
    assert schema.revenue_paise == 5000000
    assert schema.status == "completed"


def test_invalid_voyage_revenue_rejections():
    # Negative revenue rejected
    with raises(ValidationError):
        VoyageCreate(
            name="Failed Voyage",
            date=datetime.utcnow(),
            revenue_paise=-1000
        )

    # Float revenue rejected (must be integer paise)
    with raises(ValidationError):
        VoyageCreate(
            name="Float Revenue Voyage",
            date=datetime.utcnow(),
            revenue_paise=50000.75
        )


def test_invalid_voyage_status():
    with raises(ValidationError):
        VoyageCreate(
            name="Invalid Status Voyage",
            date=datetime.utcnow(),
            revenue_paise=100000,
            status="unknown_status"
        )


# --- 4. Expense Schema Tests ---

def test_valid_expense_create():
    schema = ExpenseCreate(
        voyage_id=1,
        category="Gunpowder",
        amount_paise=125000,
        description="20 barrels of high-grade gunpowder"
    )
    assert schema.voyage_id == 1
    assert schema.category == "Gunpowder"
    assert schema.amount_paise == 125000


def test_invalid_expense_amounts():
    # Zero expense rejected
    with raises(ValidationError):
        ExpenseCreate(voyage_id=1, category="Rum", amount_paise=0)

    # Negative expense rejected
    with raises(ValidationError):
        ExpenseCreate(voyage_id=1, category="Rum", amount_paise=-500)

    # Float expense rejected
    with raises(ValidationError):
        ExpenseCreate(voyage_id=1, category="Rum", amount_paise=850.50)


# --- 5. Transaction Schema Tests ---

def test_valid_transaction_response():
    schema = TransactionResponse(
        id=1,
        voyage_id=10,
        transaction_type="CREDIT",
        amount_paise=5000000,
        description="Gross voyage revenue from Spanish Galleon",
        timestamp=datetime.utcnow(),
        reference_type="voyage_revenue",
        reference_id=10,
        created_at=datetime.utcnow()
    )
    assert schema.transaction_type == "CREDIT"
    assert schema.amount_paise == 5000000


def test_invalid_transaction_type():
    with raises(ValidationError):
        TransactionResponse(
            id=1,
            transaction_type="INVALID_TYPE",
            amount_paise=10000,
            description="Bad transaction",
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow()
        )


# --- 6. Payout Schema Tests ---

def test_payout_preview_and_reconciliation():
    item1 = PayoutPreviewItem(
        crew_member_id=1,
        crew_member_name="Edward Teach",
        rank_name="Captain",
        share_weight_units=200,
        payout_paise=4000000
    )
    item2 = PayoutPreviewItem(
        crew_member_id=2,
        crew_member_name="Jack Rackham",
        rank_name="First Mate",
        share_weight_units=150,
        payout_paise=3000000
    )

    preview = PayoutPreview(
        voyage_id=1,
        voyage_name="Expedition Alpha",
        revenue_paise=10000000,
        total_expenses_paise=3000000,
        net_profit_paise=7000000,
        total_share_units=350,
        share_value_paise=20000,
        distributable_profit_paise=7000000,
        remainder_paise=0,
        items=[item1, item2]
    )

    assert preview.net_profit_paise == 7000000
    assert len(preview.items) == 2
    assert sum(item.payout_paise for item in preview.items) == preview.distributable_profit_paise


# --- 7. Analytics Schema Tests ---

def test_dashboard_kpis_and_chart_schemas():
    kpis = DashboardKPIs(
        total_revenue_paise=25000000,
        total_expenses_paise=8000000,
        net_profit_paise=17000000,
        total_distributed_paise=17000000,
        active_crew_count=15,
        completed_voyage_count=5
    )
    assert kpis.net_profit_paise == 17000000

    chart_data = RevenueExpenseResponse(
        labels=["Voyage 1", "Voyage 2"],
        data=[
            RevenueExpensePoint(label="Voyage 1", revenue_paise=1000000, expenses_paise=300000, net_profit_paise=700000),
            RevenueExpensePoint(label="Voyage 2", revenue_paise=1500000, expenses_paise=500000, net_profit_paise=1000000),
        ]
    )
    assert len(chart_data.labels) == 2
    assert chart_data.data[0].net_profit_paise == 700000

    breakdown = ExpenseBreakdownResponse(
        items=[
            ExpenseBreakdownItem(category="Ship Repair", amount_paise=500000, percentage_basis_points=6250),
            ExpenseBreakdownItem(category="Gunpowder", amount_paise=300000, percentage_basis_points=3750),
        ]
    )
    assert len(breakdown.items) == 2
    assert breakdown.items[0].percentage_basis_points == 6250


# --- 8. ORM Model to Pydantic Serialization Tests ---

def test_orm_model_to_pydantic_validation():
    # Test Rank ORM -> RankResponse
    rank_orm = Rank(id=1, name="Captain", share_weight_units=200, is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    rank_schema = RankResponse.model_validate(rank_orm)
    assert rank_schema.id == 1
    assert rank_schema.name == "Captain"
    assert rank_schema.share_weight_units == 200

    # Test Voyage ORM -> VoyageResponse
    voyage_orm = Voyage(id=10, name="Tortuga Run", date=datetime.utcnow(), revenue_paise=5000000, status="completed", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    voyage_schema = VoyageResponse.model_validate(voyage_orm)
    assert voyage_schema.id == 10
    assert voyage_schema.revenue_paise == 5000000
    assert voyage_schema.status == "completed"

    # Test Expense ORM -> ExpenseResponse
    expense_orm = Expense(id=5, voyage_id=10, category="Provisions", amount_paise=250000, date=datetime.utcnow(), description="Rum barrels", created_at=datetime.utcnow())
    expense_schema = ExpenseResponse.model_validate(expense_orm)
    assert expense_schema.id == 5
    assert expense_schema.amount_paise == 250000


if __name__ == "__main__":
    print("=" * 60)
    print("Running Phase 3 Pydantic Schemas & Data Contract Test Suite")
    print("=" * 60)

    print("[1/8] Testing Valid Rank Schemas & Strict Integer Checks...")
    test_valid_rank_create()
    test_invalid_rank_share_weight_units()
    test_invalid_empty_rank_name()
    print("  -> Passed")

    print("[2/8] Testing Crew Schemas...")
    test_valid_crew_create()
    test_invalid_crew_create_rank_id()
    print("  -> Passed")

    print("[3/8] Testing Voyage Schemas & Negative/Float Rejections...")
    test_valid_voyage_create()
    test_invalid_voyage_revenue_rejections()
    test_invalid_voyage_status()
    print("  -> Passed")

    print("[4/8] Testing Expense Schemas & Zero/Negative/Float Rejections...")
    test_valid_expense_create()
    test_invalid_expense_amounts()
    print("  -> Passed")

    print("[5/8] Testing Transaction Schemas & Type Validation...")
    test_valid_transaction_response()
    test_invalid_transaction_type()
    print("  -> Passed")

    print("[6/8] Testing Payout Preview & Division Breakdown...")
    test_payout_preview_and_reconciliation()
    print("  -> Passed")

    print("[7/8] Testing Analytics & Chart.js Response Schemas...")
    test_dashboard_kpis_and_chart_schemas()
    print("  -> Passed")

    print("[8/8] Testing ORM Model to Pydantic Serialization (from_attributes)...")
    test_orm_model_to_pydantic_validation()
    print("  -> Passed")

    print("=" * 60)
    print("All 8 Phase 3 Pydantic Schema test suites passed successfully! [OK]")
    print("=" * 60)
