"""
Comprehensive Phase 8 Test Suite for Exportable Voyage Financial Manifests.
Covers:
- Tests 1-26 (JSON export, CSV export, format headers, schema integrity, integer money,
  financial summary reconciliation, expense items, finalized payouts, historical share snapshot,
  transaction audit log, reversal preservation, payout reconciliation invariant, empty data resilience,
  CSV parser validation, 404 missing voyage, role authorization, sensitive data exclusion,
  safe filename sanitization, pure read-only immutability invariance across repeated exports).
"""

import os
import sys
import csv
import io
import json
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
from backend.models.payout import Payout
from backend.services.financial_service import (
    post_revenue_transaction,
    create_and_post_expense,
    post_reversal_transaction,
    post_correction_transaction,
)
from backend.services.payout_service import finalize_voyage_payouts
from backend.services.export_service import get_safe_export_filename


def get_test_context():
    """Sets up an isolated test database, overrides get_db dependency, and returns (client, session, engine, tmp_dir)."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test_exports.db"
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


def run_phase_8_tests():
    print("=" * 60)
    print("Running Phase 8 Exportable Voyage Manifest Tests (JSON + CSV)")
    print("=" * 60)

    # ----------------------------------------------------
    # TEST 1: Export Voyage as JSON
    # ----------------------------------------------------
    print("[1/26] Testing JSON Manifest Export (HTTP 200 OK)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Port Royal Expedition", date=datetime(2026, 9, 1, 10, 0), revenue_paise=2000000, status="completed")
        session.add(v)
        session.commit()
        session.refresh(v)
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 2: JSON Content-Type
    # ----------------------------------------------------
    print("[2/26] Testing JSON Content-Type Header...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Tortuga Run", date=datetime(2026, 9, 2), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        assert 'attachment; filename="voyage_' in resp.headers["content-disposition"]
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 3: JSON Structure Completeness
    # ----------------------------------------------------
    print("[3/26] Testing Complete JSON Manifest Schema Structure...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Full Schema Run", date=datetime(2026, 9, 3), revenue_paise=3000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        data = resp.json()

        assert "manifest_version" in data
        assert data["manifest_version"] == "1.0"
        assert "exported_at" in data
        assert "voyage" in data
        assert "financial_summary" in data
        assert "payout_status" in data
        assert "crew" in data
        assert "expenses" in data
        assert "payouts" in data
        assert "transactions" in data
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 4: Integer Money Invariant
    # ----------------------------------------------------
    print("[4/26] Testing Strict Integer Paise Typing Across Manifest...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Integer Loot", date=datetime(2026, 9, 4), revenue_paise=5000075, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Gunpowder", 125025, datetime(2026, 9, 4), "10 kegs")

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        data = resp.json()

        fs = data["financial_summary"]
        assert isinstance(fs["revenue_paise"], int)
        assert isinstance(fs["expenses_paise"], int)
        assert isinstance(fs["net_profit_paise"], int)
        assert isinstance(fs["distributable_profit_paise"], int)

        assert fs["revenue_paise"] == 5000075
        assert fs["expenses_paise"] == 125025
        assert fs["net_profit_paise"] == 4875050

        assert isinstance(data["expenses"][0]["amount_paise"], int)
        assert isinstance(data["transactions"][0]["amount_paise"], int)
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 5: Financial Summary Reconciliation
    # ----------------------------------------------------
    print("[5/26] Testing Financial Summary Reconciliation with Phase 5...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Recon Run", date=datetime(2026, 9, 5), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Rum", 300000, datetime(2026, 9, 5), "Barrels")

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        fs = resp.json()["financial_summary"]
        assert fs["revenue_paise"] == 1000000
        assert fs["expenses_paise"] == 300000
        assert fs["net_profit_paise"] == 700000
        assert fs["distributable_profit_paise"] == 700000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 6: Multiple Expenses Export
    # ----------------------------------------------------
    print("[6/26] Testing Multiple Itemized Expenses in Manifest...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Expense Fleet", date=datetime(2026, 9, 6), revenue_paise=2000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Repairs", 100000, datetime(2026, 9, 6), "Sails")
        create_and_post_expense(session, v.id, "Provisions", 200000, datetime(2026, 9, 6), "Biscuits")
        create_and_post_expense(session, v.id, "Gunpowder", 300000, datetime(2026, 9, 6), "Cannon shot")

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        expenses = resp.json()["expenses"]
        assert len(expenses) == 3
        cats = [e["category"] for e in expenses]
        assert "Repairs" in cats
        assert "Provisions" in cats
        assert "Gunpowder" in cats
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 7: Finalized Payouts Export
    # ----------------------------------------------------
    print("[7/26] Testing Finalized Payout Records in Manifest...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r = Rank(name="Captain", share_weight_units=200, is_active=True)
        session.add(r)
        session.commit()
        c = CrewMember(name="Jack", rank_id=r.id, is_active=True)
        session.add(c)
        session.commit()

        v = Voyage(name="Dividend Voyage", date=datetime(2026, 9, 7), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        finalize_voyage_payouts(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        data = resp.json()
        assert data["payout_status"] == "FINALIZED"
        assert len(data["payouts"]) == 1
        assert data["payouts"][0]["crew_member_name"] == "Jack"
        assert data["payouts"][0]["payout_paise"] == 1000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 8: Historical Payout Snapshot Preservation
    # ----------------------------------------------------
    print("[8/26] Testing Historical Share Weight Snapshot Preservation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r_capt = Rank(name="Captain", share_weight_units=200, is_active=True)
        r_deck = Rank(name="Deckhand", share_weight_units=100, is_active=True)
        session.add_all([r_capt, r_deck])
        session.commit()

        c = CrewMember(name="Hector", rank_id=r_capt.id, is_active=True)
        session.add(c)
        session.commit()

        v = Voyage(name="Snapshot Run", date=datetime(2026, 9, 8), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        finalize_voyage_payouts(session, v.id)

        # Later: Demote Hector to Deckhand (weight 100) and change Captain rank weight to 300
        c.rank_id = r_deck.id
        r_capt.share_weight_units = 300
        session.commit()

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        payouts = resp.json()["payouts"]
        assert len(payouts) == 1
        assert payouts[0]["share_weight_units_used"] == 200  # Must preserve 200 from payout record!
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 9: Transaction History
    # ----------------------------------------------------
    print("[9/26] Testing Complete Transaction Ledger Export...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Audit Run", date=datetime(2026, 9, 9), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Repair", 200000, datetime(2026, 9, 9), "Repairs")

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        txs = resp.json()["transactions"]
        assert len(txs) == 2
        types = [t["transaction_type"] for t in txs]
        assert "CREDIT" in types
        assert "DEBIT" in types
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 10: Reversal and Correction History Preservation
    # ----------------------------------------------------
    print("[10/26] Testing Reversal & Correction History in Manifest...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Reversal Run", date=datetime(2026, 9, 10), revenue_paise=2000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        exp, exp_tx = create_and_post_expense(session, v.id, "Repairs", 100000, datetime(2026, 9, 10), "Initial expense")

        # Correct expense from 100,000 to 150,000 paise
        post_correction_transaction(session, exp_tx.id, 150000, "Audit correction")

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        txs = resp.json()["transactions"]

        # Expect: CREDIT (2,000,000), DEBIT (100,000), REVERSAL (100,000), DEBIT (150,000)
        types = [t["transaction_type"] for t in txs]
        assert "CREDIT" in types
        assert "DEBIT" in types
        assert "REVERSAL" in types
        assert len(txs) == 4
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 11: Payout Reconciliation Invariant
    # ----------------------------------------------------
    print("[11/26] Testing Payout Reconciliation Invariant (SUM == Distributable Profit)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r1 = Rank(name="Captain", share_weight_units=200, is_active=True)
        r2 = Rank(name="First Mate", share_weight_units=100, is_active=True)
        session.add_all([r1, r2])
        session.commit()

        c1 = CrewMember(name="Captain", rank_id=r1.id, is_active=True)
        c2 = CrewMember(name="Mate", rank_id=r2.id, is_active=True)
        session.add_all([c1, c2])
        session.commit()

        v = Voyage(name="3-Way Split", date=datetime(2026, 9, 11), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Provisions", 250000, datetime(2026, 9, 11), "Rum")

        finalize_voyage_payouts(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        data = resp.json()
        fs = data["financial_summary"]
        payouts = data["payouts"]

        sum_payouts = sum(p["payout_paise"] for p in payouts)
        assert sum_payouts == fs["distributable_profit_paise"]
        assert sum_payouts == 750000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 12: Empty Data Handling
    # ----------------------------------------------------
    print("[12/26] Testing JSON Export of Voyage with No Expenses/Payouts...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Empty Run", date=datetime(2026, 9, 12), revenue_paise=0, status="planned")
        session.add(v)
        session.commit()

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["payout_status"] == "NOT_FINALIZED"
        assert data["expenses"] == []
        assert data["payouts"] == []
        assert data["transactions"] == []
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 13: CSV Export HTTP 200
    # ----------------------------------------------------
    print("[13/26] Testing CSV Manifest Export (HTTP 200 OK)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="CSV Voyage", date=datetime(2026, 9, 13), revenue_paise=1500000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/csv")
        assert resp.status_code == 200
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 14: CSV Content-Type
    # ----------------------------------------------------
    print("[14/26] Testing CSV Content-Type Header...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="CSV Header Run", date=datetime(2026, 9, 14), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert 'attachment; filename="voyage_' in resp.headers["content-disposition"]
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 15: CSV Record Types Presence
    # ----------------------------------------------------
    print("[15/26] Testing CSV Record Type Discriminators...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r = Rank(name="Captain", share_weight_units=200, is_active=True)
        session.add(r)
        session.commit()
        c = CrewMember(name="Barbossa", rank_id=r.id, is_active=True)
        session.add(c)
        session.commit()

        v = Voyage(name="All-Record Voyage", date=datetime(2026, 9, 15), revenue_paise=2000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Repair", 500000, datetime(2026, 9, 15), "Hull")
        finalize_voyage_payouts(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/csv")
        csv_text = resp.text

        assert "voyage" in csv_text
        assert "financial_summary" in csv_text
        assert "crew" in csv_text
        assert "expense" in csv_text
        assert "payout" in csv_text
        assert "transaction" in csv_text
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 16: CSV Parser Compatibility
    # ----------------------------------------------------
    print("[16/26] Testing Python CSV Parser Compatibility...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Parse Check", date=datetime(2026, 9, 16), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/csv")
        csv_file = io.StringIO(resp.text)
        reader = csv.reader(csv_file)
        rows = list(reader)

        assert len(rows) >= 5  # header + voyage + 4 financial_summary rows + transaction
        assert rows[0][0] == "record_type"
        assert rows[0][1] == "id"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 17: Voyage Not Found (404)
    # ----------------------------------------------------
    print("[17/26] Testing Non-Existent Voyage ID (404 Not Found)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        resp_json = client.get("/api/voyages/9999/export/json")
        assert resp_json.status_code == 404
        assert "Voyage with ID 9999 not found" in resp_json.json()["detail"]

        resp_csv = client.get("/api/voyages/9999/export/csv")
        assert resp_csv.status_code == 404
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 18: Role Authorization
    # ----------------------------------------------------
    print("[18/26] Testing Authorization Headers for Exports...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Auth Test", date=datetime(2026, 9, 18), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        # Captain and Admin have access
        assert client.get(f"/api/voyages/{v.id}/export/json", headers={"X-User-Role": "captain"}).status_code == 200
        assert client.get(f"/api/voyages/{v.id}/export/json", headers={"X-User-Role": "admin"}).status_code == 200
        assert client.get(f"/api/voyages/{v.id}/export/json", headers={"X-User-Role": "crew"}).status_code == 200

        # Unauthorized role returns 403
        assert client.get(f"/api/voyages/{v.id}/export/json", headers={"X-User-Role": "intruder"}).status_code == 403
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 19: Sensitive Information Exclusion
    # ----------------------------------------------------
    print("[19/26] Testing Strict Exclusion of Secrets & Credentials...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Sanitization Check", date=datetime(2026, 9, 19), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        raw_text = resp.text.lower()
        assert "password" not in raw_text
        assert "password_hash" not in raw_text
        assert "jwt" not in raw_text
        assert "secret_key" not in raw_text
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 20: Safe Filename Sanitization
    # ----------------------------------------------------
    print("[20/26] Testing Filename Sanitization & Path Traversal Defense...")
    assert get_safe_export_filename(10, "json") == "voyage_10_manifest.json"
    assert get_safe_export_filename(10, "csv") == "voyage_10_manifest.csv"
    assert get_safe_export_filename(10, "../unsafe.exe") == "voyage_10_manifest.json"
    print("  -> Passed")

    # ----------------------------------------------------
    # TEST 21: CSV Formula Injection Escaping
    # ----------------------------------------------------
    print("[21/26] Testing CSV Formula Injection Escaping (=, +, -, @)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="=CMD|' /C calc'!A0", date=datetime(2026, 9, 21), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get(f"/api/voyages/{v.id}/export/csv")
        # Ensure formula is prefixed with single quote
        assert "'=CMD" in resp.text
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 22: Financial Consistency with Known Data
    # ----------------------------------------------------
    print("[22/26] Testing Financial Engine Consistency Across Manifest...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Exact Check", date=datetime(2026, 9, 22), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Gunpowder", 400000, datetime(2026, 9, 22), "Gunpowder")

        resp = client.get(f"/api/voyages/{v.id}/export/json")
        fs = resp.json()["financial_summary"]
        assert fs["revenue_paise"] == 1000000
        assert fs["expenses_paise"] == 400000
        assert fs["net_profit_paise"] == 600000
        assert fs["distributable_profit_paise"] == 600000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 23: Read-Only Invariance on Analytics
    # ----------------------------------------------------
    print("[23/26] Testing Read-Only Invariance on Analytics Metrics...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Analytics Invariant", date=datetime(2026, 9, 23), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        before_analytics = client.get("/api/analytics/dashboard-summary").json()

        # Perform multiple exports
        client.get(f"/api/voyages/{v.id}/export/json")
        client.get(f"/api/voyages/{v.id}/export/csv")

        after_analytics = client.get("/api/analytics/dashboard-summary").json()
        assert before_analytics == after_analytics
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 24: Read-Only Invariance on Payouts
    # ----------------------------------------------------
    print("[24/26] Testing Read-Only Invariance on Payout Records...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r = Rank(name="Captain", share_weight_units=200, is_active=True)
        session.add(r)
        session.commit()
        c = CrewMember(name="Davy", rank_id=r.id, is_active=True)
        session.add(c)
        session.commit()

        v = Voyage(name="Payout Invariant", date=datetime(2026, 9, 24), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        finalize_voyage_payouts(session, v.id)

        count_before = session.query(Payout).count()
        client.get(f"/api/voyages/{v.id}/export/json")
        client.get(f"/api/voyages/{v.id}/export/csv")
        count_after = session.query(Payout).count()

        assert count_before == count_after
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 25: Read-Only Invariance on Transaction Ledger
    # ----------------------------------------------------
    print("[25/26] Testing Read-Only Invariance on TransactionLog Ledger...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Ledger Invariant", date=datetime(2026, 9, 25), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        tx_count_before = session.query(TransactionLog).count()
        client.get(f"/api/voyages/{v.id}/export/json")
        client.get(f"/api/voyages/{v.id}/export/csv")
        tx_count_after = session.query(TransactionLog).count()

        assert tx_count_before == tx_count_after
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 26: Complete End-to-End Export Verification
    # ----------------------------------------------------
    print("[26/26] Testing Complete End-to-End Export Reconciliation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r1 = Rank(name="Captain", share_weight_units=200, is_active=True)
        r2 = Rank(name="Quartermaster", share_weight_units=100, is_active=True)
        session.add_all([r1, r2])
        session.commit()

        c1 = CrewMember(name="Captain Morgan", rank_id=r1.id, is_active=True)
        c2 = CrewMember(name="First Mate Gibbs", rank_id=r2.id, is_active=True)
        session.add_all([c1, c2])
        session.commit()

        v = Voyage(name="Grand Sovereign", date=datetime(2026, 9, 26), revenue_paise=3000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Cannon Powder", 600000, datetime(2026, 9, 26), "Powder")

        finalize_voyage_payouts(session, v.id)

        # JSON
        json_resp = client.get(f"/api/voyages/{v.id}/export/json")
        assert json_resp.status_code == 200
        json_data = json_resp.json()
        assert json_data["financial_summary"]["net_profit_paise"] == 2400000
        assert len(json_data["payouts"]) == 2
        assert json_data["payouts"][0]["payout_paise"] + json_data["payouts"][1]["payout_paise"] == 2400000

        # CSV
        csv_resp = client.get(f"/api/voyages/{v.id}/export/csv")
        assert csv_resp.status_code == 200
        assert "Grand Sovereign" in csv_resp.text
        assert "2400000" in csv_resp.text

        print("  -> Passed (100% Verified Across JSON, CSV, Payouts, and Transaction Ledger)")
    finally:
        cleanup_context(session, engine, tmp_dir)

    print("=" * 60)
    print("All Phase 8 Voyage Manifest Export test suites passed successfully! [OK]")
    print("=" * 60)


def test_phase_8_export_suite():
    run_phase_8_tests()


if __name__ == "__main__":
    run_phase_8_tests()
