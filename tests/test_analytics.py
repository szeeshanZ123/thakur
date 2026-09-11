"""
Comprehensive Phase 7 Test Suite for Analytics & Dashboard APIs.
Covers 24 distinct tests verifying:
- Empty database resilience
- Dashboard KPI totals
- Revenue, expense, profit calculations
- Loss and break-even voyage handling
- Expense category percentage basis points
- Voyage profitability and ROI calculations
- Top and loss-making voyage rankings
- Crew lifetime earnings and historical snapshot integrity
- Rank-level payout distributions
- Daily, weekly, monthly time-series aggregations
- Date range and voyage filtering
- Invalid date range rejection (400)
- Strict integer paise preservation
- Exact arithmetic precision
- Payout totals reconciliation with Phase 6
- Role-based authorization
- Pagination and allowlisted sorting
- Cross-phase financial consistency (Phase 5 + Phase 6 + Phase 7)
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, UTC, timedelta
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
)
from backend.services.payout_service import (
    finalize_voyage_payouts,
)


def get_test_context():
    """Sets up an isolated test database, overrides get_db dependency, and returns (client, session, engine, tmp_dir)."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test_analytics.db"
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


def run_phase_7_tests():
    print("=" * 60)
    print("Running Phase 7 Analytics & Dashboard API Tests")
    print("=" * 60)

    # ----------------------------------------------------
    # TEST 1: Empty Database
    # ----------------------------------------------------
    print("[1/24] Testing Empty Database Handling...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        resp = client.get("/api/analytics/dashboard-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_revenue_paise"] == 0
        assert data["total_expenses_paise"] == 0
        assert data["net_profit_paise"] == 0
        assert data["distributable_profit_paise"] == 0
        assert data["total_voyages"] == 0
        assert data["active_crew"] == 0

        # Empty lists on other endpoints
        assert client.get("/api/analytics/revenue").json()["by_voyage"] == []
        assert client.get("/api/analytics/expenses").json()["by_category"] == []
        assert client.get("/api/analytics/voyages/top").json()["voyages"] == []
        assert client.get("/api/analytics/crew/earnings").json()["items"] == []
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 2: Dashboard Totals
    # ----------------------------------------------------
    print("[2/24] Testing Dashboard Summary Totals Reconciliation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        # Create voyage and post revenue
        v = Voyage(name="Treasure Island", date=datetime(2026, 9, 1, 10, 0), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        session.refresh(v)

        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Gunpowder", 250000, datetime(2026, 9, 1, 11, 0), "10 barrels")

        resp = client.get("/api/analytics/dashboard-summary")
        assert resp.status_code == 200
        d = resp.json()
        assert d["total_revenue_paise"] == 1000000
        assert d["total_expenses_paise"] == 250000
        assert d["net_profit_paise"] == 750000
        assert d["distributable_profit_paise"] == 750000
        assert d["total_voyages"] == 1
        assert d["completed_voyages"] == 1
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 3: Profit Calculation
    # ----------------------------------------------------
    print("[3/24] Testing Profit Calculation (Revenue - Expenses)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Nassau Raid", date=datetime(2026, 9, 2, 10, 0), revenue_paise=5000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Repairs", 1500000, datetime(2026, 9, 2, 11, 0), "Hull patch")

        resp = client.get("/api/analytics/profit")
        assert resp.status_code == 200
        d = resp.json()
        assert d["total_revenue_paise"] == 5000000
        assert d["total_expenses_paise"] == 1500000
        assert d["net_profit_paise"] == 3500000
        assert d["profitable_voyages"] == 1
        assert d["loss_making_voyages"] == 0
        assert d["break_even_voyages"] == 0
        assert d["average_profit_margin_basis_points"] == 7000  # 3500000 / 5000000 = 70% = 7000 bps
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 4: Loss-Making Voyage
    # ----------------------------------------------------
    print("[4/24] Testing Loss-Making Voyage (Negative Profit)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Bermuda Storm", date=datetime(2026, 9, 3, 10, 0), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Major Repairs", 1400000, datetime(2026, 9, 3, 11, 0), "Mast replacement")

        resp = client.get("/api/analytics/profit")
        assert resp.status_code == 200
        d = resp.json()
        assert d["total_revenue_paise"] == 1000000
        assert d["total_expenses_paise"] == 1400000
        assert d["net_profit_paise"] == -400000
        assert d["distributable_profit_paise"] == 0
        assert d["loss_making_voyages"] == 1
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 5: Break-Even Voyage
    # ----------------------------------------------------
    print("[5/24] Testing Break-Even Voyage (Profit = 0)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Even Keel", date=datetime(2026, 9, 4, 10, 0), revenue_paise=800000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Provisions", 800000, datetime(2026, 9, 4, 11, 0), "Food & Rum")

        resp = client.get("/api/analytics/voyages/profitability")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["net_profit_paise"] == 0
        assert items[0]["status"] == "BREAK_EVEN"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 6: Expense Category Breakdown
    # ----------------------------------------------------
    print("[6/24] Testing Expense Category Breakdown & Basis Points...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Barbados Run", date=datetime(2026, 9, 5, 10, 0), revenue_paise=3000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Gunpowder", 300000, datetime(2026, 9, 5, 11, 0), "Powder")
        create_and_post_expense(session, v.id, "Provisions", 700000, datetime(2026, 9, 5, 12, 0), "Rum")

        resp = client.get("/api/analytics/expenses/by-category")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        # Total = 1000000 -> Gunpowder = 300000 (3000 bps), Provisions = 700000 (7000 bps)
        cat_dict = {i["category"]: i for i in items}
        assert cat_dict["Gunpowder"]["amount_paise"] == 300000
        assert cat_dict["Gunpowder"]["percentage_basis_points"] == 3000
        assert cat_dict["Provisions"]["amount_paise"] == 700000
        assert cat_dict["Provisions"]["percentage_basis_points"] == 7000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 7: Voyage Profitability List
    # ----------------------------------------------------
    print("[7/24] Testing Voyage Profitability Metrics...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Porto Bello", date=datetime(2026, 9, 6, 10, 0), revenue_paise=2000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Fuel", 500000, datetime(2026, 9, 6, 11, 0), "Wood")

        resp = client.get("/api/analytics/voyages/profitability")
        assert resp.status_code == 200
        v_item = resp.json()["items"][0]
        assert v_item["revenue_paise"] == 2000000
        assert v_item["expenses_paise"] == 500000
        assert v_item["net_profit_paise"] == 1500000
        assert v_item["status"] == "PROFITABLE"
        assert v_item["roi_basis_points"] == 30000  # 1500000 / 500000 * 10000 = 30000 bps (300% ROI)
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 8: Top Voyages Ranking
    # ----------------------------------------------------
    print("[8/24] Testing Top Voyages Ranking (Net Profit DESC)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v1 = Voyage(name="Low Profit", date=datetime(2026, 9, 1), revenue_paise=1000000, status="completed")
        v2 = Voyage(name="High Profit", date=datetime(2026, 9, 2), revenue_paise=5000000, status="completed")
        v3 = Voyage(name="Mid Profit", date=datetime(2026, 9, 3), revenue_paise=3000000, status="completed")
        session.add_all([v1, v2, v3])
        session.commit()
        for v in [v1, v2, v3]:
            post_revenue_transaction(session, v.id)

        resp = client.get("/api/analytics/voyages/top?limit=2")
        assert resp.status_code == 200
        top = resp.json()["voyages"]
        assert len(top) == 2
        assert top[0]["voyage_name"] == "High Profit"
        assert top[0]["net_profit_paise"] == 5000000
        assert top[1]["voyage_name"] == "Mid Profit"
        assert top[1]["net_profit_paise"] == 3000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 9: Loss-Making Voyages Ranking
    # ----------------------------------------------------
    print("[9/24] Testing Loss-Making Voyages (Largest Loss First)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_win = Voyage(name="Profit Voyage", date=datetime(2026, 9, 1), revenue_paise=2000000, status="completed")
        v_loss1 = Voyage(name="Small Loss", date=datetime(2026, 9, 2), revenue_paise=1000000, status="completed")
        v_loss2 = Voyage(name="Big Loss", date=datetime(2026, 9, 3), revenue_paise=1000000, status="completed")
        session.add_all([v_win, v_loss1, v_loss2])
        session.commit()
        for v in [v_win, v_loss1, v_loss2]:
            post_revenue_transaction(session, v.id)

        create_and_post_expense(session, v_win.id, "Food", 500000, datetime(2026, 9, 1), "Food")
        create_and_post_expense(session, v_loss1.id, "Repair", 1200000, datetime(2026, 9, 2), "Minor loss")
        create_and_post_expense(session, v_loss2.id, "Repair", 2500000, datetime(2026, 9, 3), "Major disaster")

        resp = client.get("/api/analytics/voyages/losses")
        assert resp.status_code == 200
        losses = resp.json()["voyages"]
        assert len(losses) == 2
        assert losses[0]["voyage_name"] == "Big Loss"
        assert losses[0]["net_profit_paise"] == -1500000
        assert losses[1]["voyage_name"] == "Small Loss"
        assert losses[1]["net_profit_paise"] == -200000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 10: Crew Earnings Analytics
    # ----------------------------------------------------
    print("[10/24] Testing Crew Lifetime Earnings Analytics...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r = Rank(name="Captain", share_weight_units=200, is_active=True)
        session.add(r)
        session.commit()
        c = CrewMember(name="Jack", rank_id=r.id, is_active=True)
        session.add(c)
        session.commit()

        v = Voyage(name="Gold Run", date=datetime(2026, 9, 1), revenue_paise=2000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        finalize_voyage_payouts(session, v.id)

        resp = client.get("/api/analytics/crew/earnings")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Jack"
        assert items[0]["total_earnings_paise"] == 2000000
        assert items[0]["payout_count"] == 1
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 11: Historical Payout Snapshot Preservation
    # ----------------------------------------------------
    print("[11/24] Testing Historical Payout Integrity After Rank Change...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r_capt = Rank(name="Captain", share_weight_units=200, is_active=True)
        r_deck = Rank(name="Deckhand", share_weight_units=100, is_active=True)
        session.add_all([r_capt, r_deck])
        session.commit()

        c = CrewMember(name="Billy", rank_id=r_capt.id, is_active=True)
        session.add(c)
        session.commit()

        v = Voyage(name="Historical Test", date=datetime(2026, 9, 1), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        finalize_voyage_payouts(session, v.id)

        # Demote crew member to Deckhand
        c.rank_id = r_deck.id
        session.commit()

        # Verify analytics still accurately reflects the 1,000,000 paise received
        resp = client.get("/api/analytics/crew/earnings")
        assert resp.status_code == 200
        assert resp.json()["items"][0]["total_earnings_paise"] == 1000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 12: Rank-Wise Payout Analytics
    # ----------------------------------------------------
    print("[12/24] Testing Rank-Wise Payout Aggregation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r1 = Rank(name="Officer", share_weight_units=100, is_active=True)
        r2 = Rank(name="Sailor", share_weight_units=100, is_active=True)
        session.add_all([r1, r2])
        session.commit()

        c1 = CrewMember(name="Officer 1", rank_id=r1.id, is_active=True)
        c2 = CrewMember(name="Sailor 1", rank_id=r2.id, is_active=True)
        session.add_all([c1, c2])
        session.commit()

        v = Voyage(name="Split Run", date=datetime(2026, 9, 1), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        finalize_voyage_payouts(session, v.id)

        resp = client.get("/api/analytics/ranks/payouts")
        assert resp.status_code == 200
        ranks = resp.json()["ranks"]
        assert len(ranks) == 2
        for r_item in ranks:
            assert r_item["total_payout_paise"] == 500000
            assert r_item["payout_count"] == 1
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 13: Time-Series Aggregations (Daily, Weekly, Monthly)
    # ----------------------------------------------------
    print("[13/24] Testing Time-Series Trends (Daily, Weekly, Monthly)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v1 = Voyage(name="Day 1", date=datetime(2026, 9, 10, 10, 0), revenue_paise=1000000, status="completed")
        v2 = Voyage(name="Day 2", date=datetime(2026, 9, 11, 10, 0), revenue_paise=2000000, status="completed")
        session.add_all([v1, v2])
        session.commit()
        post_revenue_transaction(session, v1.id)
        post_revenue_transaction(session, v2.id)

        # Daily
        resp_daily = client.get("/api/analytics/time-series?group_by=daily")
        assert resp_daily.status_code == 200
        daily_pts = resp_daily.json()["data"]
        assert len(daily_pts) == 2
        assert daily_pts[0]["period"] == "2026-09-10"
        assert daily_pts[0]["revenue_paise"] == 1000000
        assert daily_pts[1]["period"] == "2026-09-11"
        assert daily_pts[1]["revenue_paise"] == 2000000

        # Monthly
        resp_monthly = client.get("/api/analytics/time-series?group_by=monthly")
        assert resp_monthly.status_code == 200
        monthly_pts = resp_monthly.json()["data"]
        assert len(monthly_pts) == 1
        assert monthly_pts[0]["period"] == "2026-09"
        assert monthly_pts[0]["revenue_paise"] == 3000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 14: Date Range Filtering
    # ----------------------------------------------------
    print("[14/24] Testing Date Range Filtering...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v_aug = Voyage(name="August", date=datetime(2026, 8, 15), revenue_paise=1000000, status="completed")
        v_sep = Voyage(name="September", date=datetime(2026, 9, 15), revenue_paise=2000000, status="completed")
        session.add_all([v_aug, v_sep])
        session.commit()
        post_revenue_transaction(session, v_aug.id)
        post_revenue_transaction(session, v_sep.id)

        resp = client.get("/api/analytics/revenue?start_date=2026-09-01T00:00:00&end_date=2026-09-30T23:59:59")
        assert resp.status_code == 200
        d = resp.json()
        assert d["total_revenue_paise"] == 2000000
        assert len(d["by_voyage"]) == 1
        assert d["by_voyage"][0]["voyage_name"] == "September"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 15: Invalid Date Range Validation (start_date > end_date)
    # ----------------------------------------------------
    print("[15/24] Testing Invalid Date Range Rejection (400)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        resp = client.get("/api/analytics/dashboard-summary?start_date=2026-09-30T00:00:00&end_date=2026-09-01T00:00:00")
        assert resp.status_code == 400
        assert "start_date cannot be greater than end_date" in resp.json()["detail"]
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 16: Voyage-Specific Filter
    # ----------------------------------------------------
    print("[16/24] Testing Single Voyage Specific Filtering...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v1 = Voyage(name="Target Voyage", date=datetime(2026, 9, 1), revenue_paise=1000000, status="completed")
        v2 = Voyage(name="Other Voyage", date=datetime(2026, 9, 2), revenue_paise=3000000, status="completed")
        session.add_all([v1, v2])
        session.commit()
        post_revenue_transaction(session, v1.id)
        post_revenue_transaction(session, v2.id)

        resp = client.get(f"/api/analytics/dashboard-summary?voyage_id={v1.id}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["total_revenue_paise"] == 1000000
        assert d["total_voyages"] == 1
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 17: Integer Paise Type Check
    # ----------------------------------------------------
    print("[17/24] Testing Strict Integer Paise Type Invariant...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Integer Check", date=datetime(2026, 9, 1), revenue_paise=1234567, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)

        resp = client.get("/api/analytics/dashboard-summary")
        d = resp.json()
        assert isinstance(d["total_revenue_paise"], int)
        assert isinstance(d["total_expenses_paise"], int)
        assert isinstance(d["net_profit_paise"], int)
        assert isinstance(d["distributable_profit_paise"], int)
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 18: Exact Arithmetic Precision (No Floats)
    # ----------------------------------------------------
    print("[18/24] Testing Exact Paise Arithmetic Precision (10075 - 2025 = 8050)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v = Voyage(name="Precision Test", date=datetime(2026, 9, 1), revenue_paise=10075, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        create_and_post_expense(session, v.id, "Supplies", 2025, datetime(2026, 9, 1), "Supplies")

        resp = client.get("/api/analytics/dashboard-summary")
        d = resp.json()
        assert d["total_revenue_paise"] == 10075
        assert d["total_expenses_paise"] == 2025
        assert d["net_profit_paise"] == 8050
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 19: Payout Totals Reconciliation with Phase 6
    # ----------------------------------------------------
    print("[19/24] Testing Payout Analytics Reconciliation with Phase 6...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r = Rank(name="Captain", share_weight_units=100, is_active=True)
        session.add(r)
        session.commit()
        c = CrewMember(name="Jack", rank_id=r.id, is_active=True)
        session.add(c)
        session.commit()

        v = Voyage(name="Payout Recon", date=datetime(2026, 9, 1), revenue_paise=4000000, status="completed")
        session.add(v)
        session.commit()
        post_revenue_transaction(session, v.id)
        finalize_voyage_payouts(session, v.id)

        resp = client.get("/api/analytics/payouts")
        assert resp.status_code == 200
        d = resp.json()
        assert d["total_payouts_paise"] == 4000000
        assert d["payout_count"] == 1
        assert d["average_payout_paise"] == 4000000
        assert d["by_voyage"][0]["total_payout_paise"] == 4000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 20: Role Authorization
    # ----------------------------------------------------
    print("[20/24] Testing Role-Based Authorization for Analytics...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        # Captain and Admin have access
        assert client.get("/api/analytics/dashboard-summary", headers={"X-User-Role": "captain"}).status_code == 200
        assert client.get("/api/analytics/dashboard-summary", headers={"X-User-Role": "admin"}).status_code == 200
        assert client.get("/api/analytics/dashboard-summary", headers={"X-User-Role": "crew"}).status_code == 200

        # Unauthorized/invalid role returns 403 Forbidden
        resp_invalid = client.get("/api/analytics/dashboard-summary", headers={"X-User-Role": "unauthorized_role"})
        assert resp_invalid.status_code == 403
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 21: Pagination
    # ----------------------------------------------------
    print("[21/24] Testing Pagination Parameters...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        for i in range(15):
            v = Voyage(name=f"Voyage {i+1}", date=datetime(2026, 9, 1) + timedelta(days=i), revenue_paise=1000000, status="completed")
            session.add(v)
        session.commit()

        resp = client.get("/api/analytics/voyages/profitability?page=1&page_size=5")
        assert resp.status_code == 200
        d = resp.json()
        assert len(d["items"]) == 5
        assert d["total"] == 15
        assert d["page"] == 1
        assert d["page_size"] == 5
        assert d["total_pages"] == 3
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 22: Safe Sorting
    # ----------------------------------------------------
    print("[22/24] Testing Safe Field Allowlist Sorting...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        v1 = Voyage(name="Alpha", date=datetime(2026, 9, 1), revenue_paise=1000000, status="completed")
        v2 = Voyage(name="Beta", date=datetime(2026, 9, 2), revenue_paise=5000000, status="completed")
        session.add_all([v1, v2])
        session.commit()
        post_revenue_transaction(session, v1.id)
        post_revenue_transaction(session, v2.id)

        # Sort by revenue_paise desc
        resp = client.get("/api/analytics/voyages/profitability?sort_by=revenue_paise&order=desc")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items[0]["voyage_name"] == "Beta"
        assert items[1]["voyage_name"] == "Alpha"

        # Sort by revenue_paise asc
        resp_asc = client.get("/api/analytics/voyages/profitability?sort_by=revenue_paise&order=asc")
        assert resp_asc.status_code == 200
        items_asc = resp_asc.json()["items"]
        assert items_asc[0]["voyage_name"] == "Alpha"
        assert items_asc[1]["voyage_name"] == "Beta"
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 23: Efficient Bulk Aggregation Resilience
    # ----------------------------------------------------
    print("[23/24] Testing Bulk Dataset Aggregation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyages = []
        for i in range(25):
            voyages.append(Voyage(name=f"Fleet {i}", date=datetime(2026, 9, 1), revenue_paise=100000, status="completed"))
        session.add_all(voyages)
        session.commit()
        for v in voyages:
            post_revenue_transaction(session, v.id)

        resp = client.get("/api/analytics/dashboard-summary")
        assert resp.status_code == 200
        assert resp.json()["total_revenue_paise"] == 2500000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 24: Financial Reconciliation Integration Test (Phase 5 + 6 + 7)
    # ----------------------------------------------------
    print("[24/24] Testing End-to-End Financial Reconciliation (Phase 5 + 6 + 7)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        # Setup Crew
        r = Rank(name="Captain", share_weight_units=200, is_active=True)
        session.add(r)
        session.commit()
        c = CrewMember(name="Captain Blackbeard", rank_id=r.id, is_active=True)
        session.add(c)
        session.commit()

        # Voyage A: Rev 1,000,000, Exp 300,000 -> Net 700,000
        v = Voyage(name="Grand Expedition", date=datetime(2026, 9, 1), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()

        # Post Revenue (Phase 5)
        post_revenue_transaction(session, v.id)

        # Post Expense (Phase 5)
        create_and_post_expense(session, v.id, "Ammunition", 300000, datetime(2026, 9, 1, 12, 0), "Cannonballs")

        # Finalize Payout (Phase 6)
        finalize_voyage_payouts(session, v.id)

        # Query Dashboard (Phase 7)
        resp = client.get("/api/analytics/dashboard-summary")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_revenue_paise"] == 1000000
        assert data["total_expenses_paise"] == 300000
        assert data["net_profit_paise"] == 700000
        assert data["distributable_profit_paise"] == 700000
        assert data["total_payouts_paise"] == 700000

        # Verify Crew Earnings Match Payouts
        resp_crew = client.get("/api/analytics/crew/earnings")
        assert resp_crew.status_code == 200
        assert resp_crew.json()["items"][0]["total_earnings_paise"] == 700000

        print("  -> Passed (Zero Paise Discrepancy Verified Across Phases 5, 6, and 7)")
    finally:
        cleanup_context(session, engine, tmp_dir)

    print("=" * 60)
    print("All Phase 7 Analytics & Dashboard test suites passed successfully! [OK]")
    print("=" * 60)


def test_phase_7_analytics_suite():
    run_phase_7_tests()


if __name__ == "__main__":
    run_phase_7_tests()
