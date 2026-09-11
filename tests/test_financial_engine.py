"""
Comprehensive Phase 5 Test Suite for Financial Engine and Immutable Ledger.
Covers:
- Tests 1-14 (Revenue only, Revenue+Expense, Loss/Negative Profit, Paise Precision, Multiple Expenses,
  CREDIT/DEBIT postings, Immutability (no PUT/DELETE), Reversals, Corrections, Duplicate Idempotency,
  Atomic Rollback, Financial Summary reconciliation).
- Exact zero-loss integer math and append-only audit trail verification.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.core.database import Base, get_db
from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog
from backend.models.rank import Rank
from backend.models.crew import CrewMember
from backend.services.financial_service import (
    calculate_voyage_effective_revenue,
    calculate_voyage_effective_expenses,
    calculate_net_profit,
    calculate_distributable_profit,
    post_revenue_transaction,
    create_and_post_expense,
    post_reversal_transaction,
    post_correction_transaction,
    get_voyage_financial_summary,
)


def get_test_context():
    """Sets up an isolated test database, overrides get_db dependency, and returns (client, session, engine, tmp_dir)."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test_fin.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    session = TestingSessionLocal()
    return client, session, engine, tmp_dir


def cleanup_context(session, engine, tmp_dir):
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()
    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass


def run_phase_5_tests():
    print("=" * 60)
    print("Running Phase 5 Financial Engine & Immutable Ledger Tests")
    print("=" * 60)

    # ----------------------------------------------------
    # TEST 1: Revenue only (₹10,000 revenue, ₹0 expenses)
    # ----------------------------------------------------
    print("[1/14] Testing Revenue Only (Net Profit = Revenue)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Port Royal Raid", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        post_revenue_transaction(session, voyage.id)
        summary = get_voyage_financial_summary(session, voyage.id)

        assert summary["revenue_paise"] == 1000000, f"Expected 1000000, got {summary['revenue_paise']}"
        assert summary["expenses_paise"] == 0, f"Expected 0, got {summary['expenses_paise']}"
        assert summary["net_profit_paise"] == 1000000, f"Expected 1000000, got {summary['net_profit_paise']}"
        assert summary["distributable_profit_paise"] == 1000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 2: Revenue + Expense (₹10,000 rev, ₹2,500 exp -> ₹7,500)
    # ----------------------------------------------------
    print("[2/14] Testing Revenue + Operational Expense...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Hispaniola Run", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        post_revenue_transaction(session, voyage.id)
        create_and_post_expense(session, voyage.id, "Gunpowder", 250000, datetime.now(UTC), "20 kegs")

        summary = get_voyage_financial_summary(session, voyage.id)
        assert summary["revenue_paise"] == 1000000
        assert summary["expenses_paise"] == 250000
        assert summary["net_profit_paise"] == 750000
        assert summary["distributable_profit_paise"] == 750000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 3: Loss / Negative Profit (₹10k rev, ₹12k exp -> -₹2k)
    # ----------------------------------------------------
    print("[3/14] Testing Loss / Negative Net Profit with 0 Distributable Profit...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Cursed Treasure Hunt", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        post_revenue_transaction(session, voyage.id)
        create_and_post_expense(session, voyage.id, "Vessel Repairs", 1200000, datetime.now(UTC), "Hull shattered")

        summary = get_voyage_financial_summary(session, voyage.id)
        assert summary["revenue_paise"] == 1000000
        assert summary["expenses_paise"] == 1200000
        assert summary["net_profit_paise"] == -200000, f"Expected -200000, got {summary['net_profit_paise']}"
        assert summary["distributable_profit_paise"] == 0, f"Expected 0 distributable, got {summary['distributable_profit_paise']}"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 4: Paise Precision (₹100.75 rev, ₹20.25 exp -> 8050 paise)
    # ----------------------------------------------------
    print("[4/14] Testing Strict Zero-Loss Integer Paise Precision...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Nassau Smuggle", date=datetime.now(UTC), revenue_paise=10075, status="completed")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        post_revenue_transaction(session, voyage.id)
        create_and_post_expense(session, voyage.id, "Harbor Duty", 2025, datetime.now(UTC), "Port tax")

        summary = get_voyage_financial_summary(session, voyage.id)
        assert summary["revenue_paise"] == 10075
        assert summary["expenses_paise"] == 2025
        assert summary["net_profit_paise"] == 8050
        assert isinstance(summary["revenue_paise"], int)
        assert isinstance(summary["expenses_paise"], int)
        assert isinstance(summary["net_profit_paise"], int)
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 5: Multiple Expenses Aggregation
    # ----------------------------------------------------
    print("[5/14] Testing Multiple Expenses Aggregation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Grand Armada", date=datetime.now(UTC), revenue_paise=5000000, status="completed")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        post_revenue_transaction(session, voyage.id)
        create_and_post_expense(session, voyage.id, "Gunpowder", 300000, datetime.now(UTC))
        create_and_post_expense(session, voyage.id, "Provisions", 200000, datetime.now(UTC))
        create_and_post_expense(session, voyage.id, "Ship Repair", 500000, datetime.now(UTC))
        create_and_post_expense(session, voyage.id, "Bribes", 150000, datetime.now(UTC))

        summary = get_voyage_financial_summary(session, voyage.id)
        assert summary["expenses_paise"] == 1150000
        assert summary["net_profit_paise"] == 3850000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 6: Revenue CREDIT Transaction Created Atomically
    # ----------------------------------------------------
    print("[6/14] Testing Revenue CREDIT Transaction Creation & Integrity...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Barbados Raid", date=datetime.now(UTC), revenue_paise=3000000, status="completed")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        tx = post_revenue_transaction(session, voyage.id, description="Raid plunder")
        assert tx.id is not None
        assert tx.voyage_id == voyage.id
        assert tx.transaction_type == "CREDIT"
        assert tx.amount_paise == 3000000
        assert tx.reference_type == "voyage_revenue"
        assert tx.reference_id == voyage.id
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 7: Expense DEBIT Transaction Created Atomically
    # ----------------------------------------------------
    print("[7/14] Testing Expense DEBIT Transaction Creation & Reference Link...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Bermuda Patrol", date=datetime.now(UTC), revenue_paise=1000000, status="ongoing")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        expense, tx = create_and_post_expense(session, voyage.id, "Rum", 45000, datetime.now(UTC), "Catering")
        assert expense.id is not None
        assert tx.id is not None
        assert tx.voyage_id == voyage.id
        assert tx.transaction_type == "DEBIT"
        assert tx.amount_paise == 45000
        assert tx.reference_type == "expense"
        assert tx.reference_id == expense.id
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 8 & 9: Immutability (Cannot Update / Cannot Delete Transactions via API)
    # ----------------------------------------------------
    print("[8/14] Testing Transaction Immutability (PUT /api/transactions blocked)...")
    print("[9/14] Testing Transaction Immutability (DELETE /api/transactions blocked)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_resp = client.post("/api/voyages", json={
            "name": "Immutable Test Voyage",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 2000000,
            "status": "completed"
        })
        v_id = v_resp.json()["id"]

        rev_resp = client.post(f"/api/voyages/{v_id}/revenue/post")
        assert rev_resp.status_code == 201
        tx_id = rev_resp.json()["id"]

        # Attempt PUT -> 405 Method Not Allowed
        put_resp = client.put(f"/api/transactions/{tx_id}", json={"amount_paise": 500})
        assert put_resp.status_code == 405, f"Expected 405, got {put_resp.status_code}"

        # Attempt DELETE -> 405 Method Not Allowed
        del_resp = client.delete(f"/api/transactions/{tx_id}")
        assert del_resp.status_code == 405, f"Expected 405, got {del_resp.status_code}"

        # Verify transaction is intact
        get_tx = client.get(f"/api/transactions/{tx_id}")
        assert get_tx.status_code == 200
        assert get_tx.json()["amount_paise"] == 2000000
        print("  -> Passed (PUT and DELETE both return HTTP 405 Method Not Allowed)")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 10: Reversal Creates NEW Transaction & Preserves Original
    # ----------------------------------------------------
    print("[10/14] Testing Reversal Mechanism (Append-Only Audit)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_id = client.post("/api/voyages", json={
            "name": "Reversal Voyage",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 5000000,
            "status": "completed"
        }).json()["id"]

        # Post revenue
        tx_rev = client.post(f"/api/voyages/{v_id}/revenue/post").json()
        tx_id = tx_rev["id"]

        # Reverse transaction via API
        rev_resp = client.post(f"/api/transactions/{tx_id}/reverse", json={
            "reason": "Auditor noted wrong chest inventory count"
        })
        assert rev_resp.status_code == 201
        reversal_tx = rev_resp.json()
        assert reversal_tx["transaction_type"] == "REVERSAL"
        assert reversal_tx["amount_paise"] == 5000000
        assert reversal_tx["reference_type"] == "transaction"
        assert reversal_tx["reference_id"] == tx_id

        # Original transaction must still exist and be unchanged
        orig_tx = client.get(f"/api/transactions/{tx_id}").json()
        assert orig_tx["transaction_type"] == "CREDIT"
        assert orig_tx["amount_paise"] == 5000000

        # Effective revenue should now be 0
        summary = client.get(f"/api/voyages/{v_id}/financial-summary").json()
        assert summary["revenue_paise"] == 0
        assert summary["net_profit_paise"] == 0

        # Attempting to reverse the same transaction again -> 409 Conflict
        dup_rev = client.post(f"/api/transactions/{tx_id}/reverse", json={"reason": "Duplicate attempt"})
        assert dup_rev.status_code == 409
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 11: Correction Preserves Complete History
    # ----------------------------------------------------
    print("[11/14] Testing Correction Mechanism (Reversal + Corrected Entry)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_id = client.post("/api/voyages", json={
            "name": "Correction Voyage",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 1000000,
            "status": "completed"
        }).json()["id"]

        client.post(f"/api/voyages/{v_id}/revenue/post")

        # Create expense of 100000 paise (₹1,000)
        exp_resp = client.post("/api/expenses", json={
            "voyage_id": v_id,
            "category": "Canvas",
            "amount_paise": 100000
        })
        assert exp_resp.status_code == 201

        # Find debit transaction
        txs = client.get(f"/api/voyages/{v_id}/transactions").json()
        debit_tx = next(t for t in txs if t["transaction_type"] == "DEBIT")

        # Correct amount from 100000 to 120000 paise (₹1,200)
        corr_resp = client.post(f"/api/transactions/{debit_tx['id']}/correct", json={
            "new_amount_paise": 120000,
            "reason": "Supplier invoice adjustment"
        })
        assert corr_resp.status_code == 201
        corr_data = corr_resp.json()
        assert len(corr_data) == 2
        assert corr_data[0]["transaction_type"] == "REVERSAL"
        assert corr_data[1]["transaction_type"] == "DEBIT"
        assert corr_data[1]["amount_paise"] == 120000

        # Check financial summary reflects effective ₹1,200 expense and ₹8,800 net profit
        summary = client.get(f"/api/voyages/{v_id}/financial-summary").json()
        assert summary["expenses_paise"] == 120000
        assert summary["net_profit_paise"] == 880000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 12: Duplicate Revenue Posting Idempotency Guard (409 Conflict)
    # ----------------------------------------------------
    print("[12/14] Testing Duplicate Revenue Posting Idempotency Guard...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_id = client.post("/api/voyages", json={
            "name": "Idempotency Voyage",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 2500000,
            "status": "completed"
        }).json()["id"]

        # Post revenue 1st time -> 201
        p1 = client.post(f"/api/voyages/{v_id}/revenue/post")
        assert p1.status_code == 201

        # Post revenue 2nd time -> 409 Conflict
        p2 = client.post(f"/api/voyages/{v_id}/revenue/post")
        assert p2.status_code == 409
        assert "already been posted" in p2.json()["detail"]
        print("  -> Passed (HTTP 409 Conflict raised on duplicate posting)")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 13: Atomic Rollback on Failure
    # ----------------------------------------------------
    print("[13/14] Testing Atomic Rollback on Posting Failure...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Rollback Voyage", date=datetime.now(UTC), revenue_paise=1000000, status="cancelled")
        session.add(voyage)
        session.commit()
        session.refresh(voyage)

        # Attempt to post revenue on cancelled voyage -> should fail and roll back
        try:
            post_revenue_transaction(session, voyage.id)
            assert False, "Should have raised HTTPException for cancelled voyage"
        except Exception:
            pass

        # Verify no transaction log entry exists
        tx_count = session.query(TransactionLog).filter(TransactionLog.voyage_id == voyage.id).count()
        assert tx_count == 0, f"Expected 0 transactions, found {tx_count}"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 14: Financial Summary Matches Ledger End-to-End
    # ----------------------------------------------------
    print("[14/14] Testing Financial Summary & Ledger End-to-End Match...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_id = client.post("/api/voyages", json={
            "name": "Full Audit Expedition",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 10000000,  # ₹100,000
            "status": "completed"
        }).json()["id"]

        client.post(f"/api/voyages/{v_id}/revenue/post")
        client.post("/api/expenses", json={"voyage_id": v_id, "category": "Repair", "amount_paise": 2000000})  # ₹20,000
        client.post("/api/expenses", json={"voyage_id": v_id, "category": "Food", "amount_paise": 1500000})    # ₹15,000

        # Query financial summary
        summary_resp = client.get(f"/api/voyages/{v_id}/financial-summary")
        assert summary_resp.status_code == 200
        sum_data = summary_resp.json()

        assert sum_data["voyage_id"] == v_id
        assert sum_data["revenue_paise"] == 10000000
        assert sum_data["expenses_paise"] == 3500000
        assert sum_data["net_profit_paise"] == 6500000
        assert sum_data["distributable_profit_paise"] == 6500000

        # Query transactions list for voyage
        tx_resp = client.get(f"/api/voyages/{v_id}/transactions")
        assert tx_resp.status_code == 200
        txs = tx_resp.json()
        assert len(txs) == 3

        credits = sum(t["amount_paise"] for t in txs if t["transaction_type"] == "CREDIT")
        debits = sum(t["amount_paise"] for t in txs if t["transaction_type"] == "DEBIT")
        assert credits == sum_data["revenue_paise"]
        assert debits == sum_data["expenses_paise"]
        assert (credits - debits) == sum_data["net_profit_paise"]
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 15: Negative Profit / Zero Distributable Profit
    # ----------------------------------------------------
    print("[15/18] Testing Negative Profit & Zero Distributable Profit Invariant...")
    client, session, engine, tmp_dir = get_test_context()

    try:
        voyage = Voyage(name="Loss Voyage", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        post_revenue_transaction(session, voyage.id)
        create_and_post_expense(session, voyage.id, "Repair", 1500000, datetime.now(UTC))

        summary = get_voyage_financial_summary(session, voyage.id)
        assert summary["net_profit_paise"] == -500000
        assert summary["distributable_profit_paise"] == 0
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 16: Zero / Negative Amount Validation
    # ----------------------------------------------------
    print("[16/18] Testing Zero/Negative Amount Rejection...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_id = client.post("/api/voyages", json={
            "name": "Validation Voyage",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 1000000,
            "status": "ongoing"
        }).json()["id"]

        # Reject negative expense
        resp_neg_exp = client.post("/api/expenses", json={"voyage_id": v_id, "category": "Food", "amount_paise": -500})
        assert resp_neg_exp.status_code == 422

        # Reject zero expense
        resp_zero_exp = client.post("/api/expenses", json={"voyage_id": v_id, "category": "Food", "amount_paise": 0})
        assert resp_zero_exp.status_code == 422

        # Reject negative revenue
        resp_neg_rev = client.post(f"/api/voyages/{v_id}/revenue/post", json={"revenue_paise": -500})
        assert resp_neg_rev.status_code == 422
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 17: Role-based Authorization on Financial Mutations
    # ----------------------------------------------------
    print("[17/18] Testing Role Authorization (CREW blocked with 403, CAPTAIN/ADMIN authorized)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_id = client.post("/api/voyages", json={
            "name": "Auth Voyage",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 5000000,
            "status": "completed"
        }).json()["id"]

        # CREW cannot post revenue
        resp_crew_rev = client.post(f"/api/voyages/{v_id}/revenue/post", headers={"X-User-Role": "crew"})
        assert resp_crew_rev.status_code == 403

        # CAPTAIN can post revenue
        resp_cap_rev = client.post(f"/api/voyages/{v_id}/revenue/post", headers={"X-User-Role": "captain"})
        assert resp_cap_rev.status_code == 201
        tx_id = resp_cap_rev.json()["id"]

        # CREW cannot record expenses
        resp_crew_exp = client.post("/api/expenses", json={"voyage_id": v_id, "category": "Rum", "amount_paise": 50000}, headers={"X-User-Role": "crew"})
        assert resp_crew_exp.status_code == 403

        # CAPTAIN can record expenses
        resp_cap_exp = client.post("/api/expenses", json={"voyage_id": v_id, "category": "Rum", "amount_paise": 50000}, headers={"X-User-Role": "captain"})
        assert resp_cap_exp.status_code == 201

        # CREW cannot reverse transactions
        resp_crew_rev_tx = client.post(f"/api/transactions/{tx_id}/reverse", json={"reason": "Audit"}, headers={"X-User-Role": "crew"})
        assert resp_crew_rev_tx.status_code == 403

        # ADMIN can reverse transactions
        resp_admin_rev_tx = client.post(f"/api/transactions/{tx_id}/reverse", json={"reason": "Audit"}, headers={"X-User-Role": "admin"})
        assert resp_admin_rev_tx.status_code == 201
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 18: Historical Snapshot Immutability
    # ----------------------------------------------------
    print("[18/18] Testing Historical Transaction Record Immutability on Entity Updates...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_id = client.post("/api/voyages", json={
            "name": "Original Name",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 3000000,
            "status": "completed"
        }).json()["id"]

        rev_tx = client.post(f"/api/voyages/{v_id}/revenue/post").json()
        tx_id = rev_tx["id"]

        # Update voyage metadata
        client.put(f"/api/voyages/{v_id}", json={"name": "Altered Name", "status": "ongoing"})

        # Verify transaction log entry remains unchanged
        stored_tx = client.get(f"/api/transactions/{tx_id}").json()
        assert stored_tx["amount_paise"] == 3000000
        assert stored_tx["transaction_type"] == "CREDIT"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    print("=" * 60)
    print("All Phase 5 Financial Engine test suites passed successfully! [OK]")
    print("=" * 60)


def test_phase_5_financial_engine_suite():
    run_phase_5_tests()


if __name__ == "__main__":
    run_phase_5_tests()

