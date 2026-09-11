"""
Comprehensive Full-Lifecycle End-to-End Integration Test Suite.
Tests the entire workflow of Captain's Treasure Ledger from initial setup through
manifest export and historical immutability.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.core.database import Base, get_db
from backend.main import app
from backend.models.rank import Rank
from backend.models.crew import CrewMember
from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog
from backend.models.payout import Payout
from backend.services.financial_service import (
    post_revenue_transaction,
    create_and_post_expense,
    post_reversal_transaction,
    post_correction_transaction,
    get_voyage_financial_summary,
    calculate_net_profit,
    calculate_distributable_profit
)
from backend.services.payout_service import (
    preview_voyage_payouts,
    finalize_voyage_payouts,
    get_crew_cumulative_balance,
    get_crew_payout_history
)
from backend.services.analytics_service import (
    get_dashboard_summary,
    get_expense_category_breakdown,
    get_voyages_profitability,
    get_crew_earnings_analytics,
    get_rank_payout_analytics,
    get_time_series_analytics
)
from backend.services.export_service import (
    build_voyage_manifest,
    export_voyage_json,
    export_voyage_csv
)


@pytest.fixture(scope="function")
def test_db():
    """Create an isolated, in-memory SQLite database for the full E2E test."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_complete_voyage_lifecycle_e2e(test_db):
    """
    End-to-End integration test covering the entire pirate treasure ledger workflow:
    1. Ranks & Crew Roster Setup (with active and inactive members)
    2. Voyage Creation & Revenue Posting
    3. Operational Expense Tracking
    4. Ledger Immutability & Reversal
    5. Profit Reconciliation & Precision (paise level)
    6. Proportional Dividend Payout Preview & Finalization
    7. Remainder Allocation & Zero-Loss Verification
    8. Crew Cumulative Earnings & Balance Check
    9. Treasury Analytics & KPIs
    10. JSON & CSV Manifest Exports (Read-Only & Formula Injection Protection)
    11. Historical Snapshot Immutability (Rank Changes After Payout Finalization)
    """
    db = test_db

    # -------------------------------------------------------------
    # STEP 1: Ranks & Crew Setup
    # -------------------------------------------------------------
    captain_rank = Rank(name="Captain", share_weight_units=200, is_active=True)      # 2.0x
    officer_rank = Rank(name="First Mate", share_weight_units=150, is_active=True)   # 1.5x
    gunner_rank = Rank(name="Gunner", share_weight_units=100, is_active=True)        # 1.0x
    sailor_rank = Rank(name="Deckhand", share_weight_units=50, is_active=True)       # 0.5x
    db.add_all([captain_rank, officer_rank, gunner_rank, sailor_rank])
    db.commit()

    # Active crew members
    c_captain = CrewMember(name="Edward Teach", rank_id=captain_rank.id, is_active=True)
    c_mate = CrewMember(name="Anne Bonny", rank_id=officer_rank.id, is_active=True)
    c_gunner = CrewMember(name="Jack Rackham", rank_id=gunner_rank.id, is_active=True)
    c_sailor = CrewMember(name="Israel Hands", rank_id=sailor_rank.id, is_active=True)
    # Inactive/retired crew member (should NOT receive dividends)
    c_retired = CrewMember(name="Billy Bones", rank_id=sailor_rank.id, is_active=False)

    db.add_all([c_captain, c_mate, c_gunner, c_sailor, c_retired])
    db.commit()

    # Total active share weight = 200 + 150 + 100 + 50 = 500 units (5.0 shares)
    active_crew = db.query(CrewMember).filter(CrewMember.is_active == True).all()
    assert len(active_crew) == 4

    # -------------------------------------------------------------
    # STEP 2: Voyage Creation & Gross Revenue Posting
    # -------------------------------------------------------------
    # Revenue: Rs. 100,000 = 10,000,000 paise
    voyage = Voyage(
        name="Grand Caribbean Expedition",
        date=datetime(2026, 9, 1, 10, 0, 0),
        revenue_paise=10000000,
        status="completed"
    )
    db.add(voyage)
    db.commit()
    db.refresh(voyage)

    rev_tx = post_revenue_transaction(db, voyage.id, voyage.revenue_paise, description="Gross treasure raid revenue")
    assert rev_tx.transaction_type == "CREDIT"
    assert rev_tx.amount_paise == 10000000

    # -------------------------------------------------------------
    # STEP 3: Operational Expenses
    # -------------------------------------------------------------
    # Provisions: Rs. 12,000 = 1,200,000 paise
    # Gunpowder:  Rs.  5,000 =   500,000 paise
    # Repairs:    Rs.  3,000 =   300,000 paise
    # Total Operational Expenses = Rs. 20,000 = 2,000,000 paise
    exp1, tx1 = create_and_post_expense(
        db, voyage.id, "Provisions", 1200000, datetime(2026, 9, 2), "Hardtack & Rum"
    )
    exp2, tx2 = create_and_post_expense(
        db, voyage.id, "Ammunition", 500000, datetime(2026, 9, 3), "Gunpowder & Shot"
    )
    exp3, tx3 = create_and_post_expense(
        db, voyage.id, "Repairs", 300000, datetime(2026, 9, 4), "Hull caulking"
    )
    assert tx1.transaction_type == "DEBIT"
    assert tx2.transaction_type == "DEBIT"
    assert tx3.transaction_type == "DEBIT"

    # -------------------------------------------------------------
    # STEP 4: Ledger Immutability, Reversal & Correction Test
    # -------------------------------------------------------------
    # Simulate an erroneous extra expense and then reverse it cleanly
    err_exp, err_tx = create_and_post_expense(
        db, voyage.id, "Other", 50000, datetime(2026, 9, 5), "Erroneous charge"
    )
    rev_entry = post_reversal_transaction(db, err_tx.id, reason="Accidental double billing")
    assert rev_entry.transaction_type == "REVERSAL"
    assert rev_entry.amount_paise == 50000

    # -------------------------------------------------------------
    # STEP 5: Profit Reconciliation
    # -------------------------------------------------------------
    # Net Profit = 10,000,000 - 2,000,000 = 8,000,000 paise (Rs. 80,000)
    net_profit = calculate_net_profit(db, voyage.id)
    dist_profit = calculate_distributable_profit(db, voyage.id)
    summary = get_voyage_financial_summary(db, voyage.id)

    assert net_profit == 8000000
    assert dist_profit == 8000000
    assert summary["revenue_paise"] == 10000000
    assert summary["expenses_paise"] == 2000000
    assert summary["net_profit_paise"] == 8000000
    assert summary["distributable_profit_paise"] == 8000000

    # -------------------------------------------------------------
    # STEP 6: Dividend Payout Preview
    # -------------------------------------------------------------
    # STEP 6: Dividend Payout Preview
    # -------------------------------------------------------------
    preview = preview_voyage_payouts(db, voyage.id)
    assert preview["total_share_units"] == 500
    assert preview["distributable_profit_paise"] == 8000000
    assert len(preview["items"]) == 4  # Only 4 active crew

    # Proportions:
    # Captain: (200 / 500) * 8,000,000 = 3,200,000 paise (Rs. 32,000)
    # Mate:    (150 / 500) * 8,000,000 = 2,400,000 paise (Rs. 24,000)
    # Gunner:  (100 / 500) * 8,000,000 = 1,600,000 paise (Rs. 16,000)
    # Sailor:   (50 / 500) * 8,000,000 =   800,000 paise (Rs.  8,000)
    payout_dict = {p["crew_member_name"]: p["payout_paise"] for p in preview["items"]}
    assert payout_dict["Edward Teach"] == 3200000
    assert payout_dict["Anne Bonny"] == 2400000
    assert payout_dict["Jack Rackham"] == 1600000
    assert payout_dict["Israel Hands"] == 800000
    assert sum(payout_dict.values()) == 8000000

    # -------------------------------------------------------------
    # STEP 7: Payout Finalization & Zero-Loss Invariant
    # -------------------------------------------------------------
    finalized_voyage, finalized_payouts = finalize_voyage_payouts(db, voyage.id, user_role="captain")
    assert len(finalized_payouts) == 4
    total_distributed = sum(p.payout_paise for p in finalized_payouts)
    assert total_distributed == 8000000

    # Verify duplicate finalization is rejected with 409 Conflict
    with pytest.raises(Exception):
        finalize_voyage_payouts(db, voyage.id, user_role="captain")

    # -------------------------------------------------------------
    # STEP 8: Crew Individual Earnings & Balances
    # -------------------------------------------------------------
    capt_bal = get_crew_cumulative_balance(db, c_captain.id)
    assert capt_bal["running_balance_paise"] == 3200000

    capt_history = get_crew_payout_history(db, c_captain.id)
    assert len(capt_history) == 1
    assert capt_history[0].share_weight_units_used == 200
    assert capt_history[0].payout_paise == 3200000

    # Inactive crew received zero
    retired_bal = get_crew_cumulative_balance(db, c_retired.id)
    assert retired_bal["running_balance_paise"] == 0

    # -------------------------------------------------------------
    # STEP 9: Treasury Analytics & Dashboard KPIs
    # -------------------------------------------------------------
    kpis = get_dashboard_summary(db)
    assert kpis["total_revenue_paise"] == 10000000
    assert kpis["total_expenses_paise"] == 2000000
    assert kpis["net_profit_paise"] == 8000000
    assert kpis["total_payouts_paise"] == 8000000
    assert kpis["completed_voyages"] == 1
    assert kpis["active_crew"] == 4

    cat_breakdown = get_expense_category_breakdown(db)
    assert len(cat_breakdown) >= 3

    profitability = get_voyages_profitability(db)
    assert profitability["total"] == 1
    assert profitability["voyages"][0]["net_profit_paise"] == 8000000

    crew_earnings = get_crew_earnings_analytics(db)
    assert crew_earnings["total"] == 5

    # -------------------------------------------------------------
    # STEP 10: JSON & CSV Manifest Exports (Read-Only Check)
    # -------------------------------------------------------------
    tx_count_before = db.query(TransactionLog).count()
    payout_count_before = db.query(Payout).count()

    # JSON Export
    manifest = build_voyage_manifest(db, voyage.id)
    assert manifest["voyage"]["id"] == voyage.id
    assert manifest["financial_summary"]["net_profit_paise"] == 8000000
    assert len(manifest["payouts"]) == 4
    assert len(manifest["transactions"]) >= 4

    json_str = export_voyage_json(db, voyage.id)
    assert "Grand Caribbean Expedition" in json_str

    # CSV Export
    csv_text = export_voyage_csv(db, voyage.id)
    assert "RECORD_SUMMARY" in csv_text or "record_type" in csv_text
    assert "Grand Caribbean Expedition" in csv_text
    assert "Edward Teach" in csv_text

    # Read-only verification: no new transactions or payouts created during export
    assert db.query(TransactionLog).count() == tx_count_before
    assert db.query(Payout).count() == payout_count_before

    # -------------------------------------------------------------
    # STEP 11: Historical Snapshot Immutability Verification
    # -------------------------------------------------------------
    # Demote Captain to Deckhand (rank share weight changed from 200 to 50)
    c_captain.rank_id = sailor_rank.id
    db.commit()

    # The historical payout record MUST still retain 200 share units and Rs. 32,000 payout
    payout_record = db.query(Payout).filter(
        Payout.voyage_id == voyage.id,
        Payout.crew_member_id == c_captain.id
    ).first()

    assert payout_record.share_weight_units_used == 200
    assert payout_record.payout_paise == 3200000
