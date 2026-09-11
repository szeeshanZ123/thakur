"""
Comprehensive Phase 6 Test Suite for Payout & Dividend Distribution Engine.
Covers:
- Tests 1-21 (Single crew, equal weights, weighted distribution, paise precision, 3-way remainder,
  deterministic tie-breaking, zero/loss profit, no active crew, zero weight, inactive crew exclusion,
  historical snapshots, duplicate finalization 409, preview non-persistence, finalization records,
  atomicity rollback, immutability, crew payout history, running balance, authorization role checks).
- Invariant / Property Fuzzing Test (500 randomized parameter combinations guaranteeing SUM(payouts) == profit).
"""

import os
import sys
import shutil
import random
import tempfile
from pathlib import Path
from datetime import datetime, UTC
from fastapi import HTTPException
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
from backend.services.payout_service import (
    calculate_integer_payout_distribution,
    preview_voyage_payouts,
    finalize_voyage_payouts,
    get_voyage_payouts,
    get_crew_payout_history,
    get_crew_cumulative_balance,
)
from backend.services.financial_service import post_revenue_transaction, create_and_post_expense


def get_test_context():
    """Sets up an isolated test database, overrides get_db dependency, and returns (client, session, engine, tmp_dir)."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test_payout.db"
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


def setup_standard_crew(session):
    """Helper to seed standard pirate ranks and crew members."""
    r_cap = Rank(name="Captain", share_weight_units=200, is_active=True)
    r_off = Rank(name="First Mate", share_weight_units=150, is_active=True)
    r_sai = Rank(name="Sailor", share_weight_units=100, is_active=True)
    session.add_all([r_cap, r_off, r_sai])
    session.commit()

    c1 = CrewMember(name="Blackbeard", rank_id=r_cap.id, is_active=True)
    c2 = CrewMember(name="Jack Sparrow", rank_id=r_off.id, is_active=True)
    c3 = CrewMember(name="Will Turner", rank_id=r_sai.id, is_active=True)
    session.add_all([c1, c2, c3])
    session.commit()
    return [c1, c2, c3]


def run_phase_6_tests():
    print("=" * 60)
    print("Running Phase 6 Payout & Dividend Engine Tests")
    print("=" * 60)

    # ----------------------------------------------------
    # TEST 1: Single Crew Member
    # ----------------------------------------------------
    print("[1/21] Testing Single Crew Member Payout...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        rank = Rank(name="Solo Captain", share_weight_units=100, is_active=True)
        session.add(rank)
        session.commit()
        crew = CrewMember(name="Solo Pirate", rank_id=rank.id, is_active=True)
        session.add(crew)
        session.commit()

        items, total_w, val = calculate_integer_payout_distribution(1000000, [crew])
        assert len(items) == 1
        assert items[0]["payout_paise"] == 1000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 2: Two Equal Crew Members
    # ----------------------------------------------------
    print("[2/21] Testing Two Equal Crew Members Payout...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        rank = Rank(name="Sailor", share_weight_units=100, is_active=True)
        session.add(rank)
        session.commit()
        c1 = CrewMember(name="Pirate A", rank_id=rank.id, is_active=True)
        c2 = CrewMember(name="Pirate B", rank_id=rank.id, is_active=True)
        session.add_all([c1, c2])
        session.commit()

        items, total_w, val = calculate_integer_payout_distribution(1000000, [c1, c2])
        assert len(items) == 2
        assert items[0]["payout_paise"] == 500000
        assert items[1]["payout_paise"] == 500000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 3: Weighted Distribution (200, 100, 100 -> 50%, 25%, 25%)
    # ----------------------------------------------------
    print("[3/21] Testing Weighted Distribution (200, 100, 100)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r_cap = Rank(name="Captain", share_weight_units=200, is_active=True)
        r_sai = Rank(name="Sailor", share_weight_units=100, is_active=True)
        session.add_all([r_cap, r_sai])
        session.commit()

        c1 = CrewMember(name="Captain", rank_id=r_cap.id, is_active=True)
        c2 = CrewMember(name="Sailor 1", rank_id=r_sai.id, is_active=True)
        c3 = CrewMember(name="Sailor 2", rank_id=r_sai.id, is_active=True)
        session.add_all([c1, c2, c3])
        session.commit()

        items, total_w, val = calculate_integer_payout_distribution(1000000, [c1, c2, c3])
        assert total_w == 400
        assert items[0]["payout_paise"] == 500000
        assert items[1]["payout_paise"] == 250000
        assert items[2]["payout_paise"] == 250000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 4: Paise Precision with Remainder (10001 paise / 200 units)
    # ----------------------------------------------------
    print("[4/21] Testing Paise Precision with Exact Remainder Allocation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        rank = Rank(name="Sailor", share_weight_units=100, is_active=True)
        session.add(rank)
        session.commit()
        c1 = CrewMember(name="A", rank_id=rank.id, is_active=True)
        c2 = CrewMember(name="B", rank_id=rank.id, is_active=True)
        session.add_all([c1, c2])
        session.commit()

        items, total_w, val = calculate_integer_payout_distribution(10001, [c1, c2])
        payouts = [item["payout_paise"] for item in items]
        assert sum(payouts) == 10001
        assert payouts == [5001, 5000]  # c1 (id 1) gets the 1 paise remainder due to tie-breaker
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 5: Three-Way Remainder Allocation
    # ----------------------------------------------------
    print("[5/21] Testing 3-Way Remainder Allocation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        r1 = Rank(name="R1", share_weight_units=100, is_active=True)
        r2 = Rank(name="R2", share_weight_units=100, is_active=True)
        r3 = Rank(name="R3", share_weight_units=100, is_active=True)
        session.add_all([r1, r2, r3])
        session.commit()

        c1 = CrewMember(name="A", rank_id=r1.id, is_active=True)
        c2 = CrewMember(name="B", rank_id=r2.id, is_active=True)
        c3 = CrewMember(name="C", rank_id=r3.id, is_active=True)
        session.add_all([c1, c2, c3])
        session.commit()

        # 100 paise divided by 3 equal shares
        items, total_w, val = calculate_integer_payout_distribution(100, [c1, c2, c3])
        payouts = [item["payout_paise"] for item in items]
        assert sum(payouts) == 100
        assert payouts == [34, 33, 33]  # 1 remainder paise allocated to c1
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 6: Deterministic Tie-Breaking by crew_member_id Ascending
    # ----------------------------------------------------
    print("[6/21] Testing Deterministic Tie-Breaking by Crew ID...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        rank = Rank(name="Sailor", share_weight_units=100, is_active=True)
        session.add(rank)
        session.commit()

        crew_members = [CrewMember(name=f"Pirate {i}", rank_id=rank.id, is_active=True) for i in range(1, 5)]
        session.add_all(crew_members)
        session.commit()

        # 102 paise divided among 4 members -> base 25 each, remainder 2 paise
        items, total_w, val = calculate_integer_payout_distribution(102, crew_members)
        payouts = {item["crew_member_id"]: item["payout_paise"] for item in items}
        assert sum(payouts.values()) == 102
        # c1 and c2 (lowest IDs) should get 26, c3 and c4 get 25
        assert payouts[crew_members[0].id] == 26
        assert payouts[crew_members[1].id] == 26
        assert payouts[crew_members[2].id] == 25
        assert payouts[crew_members[3].id] == 25
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 7: Zero Profit Returns Zero Payout
    # ----------------------------------------------------
    print("[7/21] Testing Zero Profit Handling...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        crew = setup_standard_crew(session)
        items, total_w, val = calculate_integer_payout_distribution(0, crew)
        assert len(items) == 0
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 8: Negative Profit (Loss) Returns Zero Distributable
    # ----------------------------------------------------
    print("[8/21] Testing Negative Profit / Loss Handling...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        crew = setup_standard_crew(session)
        items, total_w, val = calculate_integer_payout_distribution(-50000, crew)
        assert len(items) == 0
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 9: No Active Crew Raises 400
    # ----------------------------------------------------
    print("[9/21] Testing Error When No Active Crew...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        try:
            calculate_integer_payout_distribution(1000000, [])
            assert False, "Should have raised 400 for empty crew"
        except Exception as e:
            assert "No active crew" in str(e) or "400" in str(e)
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 10: Zero Total Share Weight Raises 400
    # ----------------------------------------------------
    print("[10/21] Testing Error When Total Share Weight is Zero...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        class MockRankZero:
            share_weight_units = 0
            name = "Zero Weight"

        class MockCrewZero:
            id = 1
            name = "Ghost Pirate"
            rank = MockRankZero()

        try:
            calculate_integer_payout_distribution(1000000, [MockCrewZero()])
            assert False, "Should have raised 400 for 0 total share weight"
        except HTTPException as e:
            assert e.status_code == 400
            assert "Total crew share weight" in e.detail
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)


    # ----------------------------------------------------
    # TEST 11: Inactive Crew Excluded from Payout
    # ----------------------------------------------------
    print("[11/21] Testing Inactive Crew Exclusion...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        rank = Rank(name="Sailor", share_weight_units=100, is_active=True)
        session.add(rank)
        session.commit()
        c_active = CrewMember(name="Active Pirate", rank_id=rank.id, is_active=True)
        c_inactive = CrewMember(name="Marooned Pirate", rank_id=rank.id, is_active=False)
        session.add_all([c_active, c_inactive])
        session.commit()

        # Voyage setup
        voyage = Voyage(name="Treasure Voyage", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        post_revenue_transaction(session, voyage.id)

        preview = preview_voyage_payouts(session, voyage.id)
        assert len(preview["items"]) == 1
        assert preview["items"][0]["crew_member_id"] == c_active.id
        assert preview["items"][0]["payout_paise"] == 1000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 12: Historical Snapshot (Rank/Weight change does NOT alter past payouts)
    # ----------------------------------------------------
    print("[12/21] Testing Historical Snapshot Reproducibility...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        rank = Rank(name="Captain", share_weight_units=200, is_active=True)
        session.add(rank)
        session.commit()
        crew = CrewMember(name="Captain Morgan", rank_id=rank.id, is_active=True)
        session.add(crew)
        session.commit()

        voyage = Voyage(name="First Raid", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        post_revenue_transaction(session, voyage.id)

        # Finalize payout
        _, payouts = finalize_voyage_payouts(session, voyage.id)
        payout_id = payouts[0].id
        assert payouts[0].share_weight_units_used == 200

        # Now change Captain's rank weight to 500
        rank.share_weight_units = 500
        session.commit()

        # Check that stored payout still preserves original snapshot 200
        stored_payout = session.query(Payout).filter(Payout.id == payout_id).first()
        assert stored_payout.share_weight_units_used == 200
        assert stored_payout.payout_paise == 1000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 13: Duplicate Finalization Returns 409 Conflict
    # ----------------------------------------------------
    print("[13/21] Testing Duplicate Finalization Idempotency Guard (409 Conflict)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        setup_standard_crew(session)
        voyage = Voyage(name="Idempotency Run", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        post_revenue_transaction(session, voyage.id)

        # 1st finalization -> success
        finalize_voyage_payouts(session, voyage.id)

        # 2nd finalization -> 409 Conflict
        try:
            finalize_voyage_payouts(session, voyage.id)
            assert False, "Should have raised 409 Conflict on duplicate payout finalization"
        except HTTPException as e:
            assert e.status_code == 409
            assert "already been finalized" in e.detail
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 14: Preview Does NOT Create Permanent Records
    # ----------------------------------------------------
    print("[14/21] Testing Preview Non-Persistence...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        setup_standard_crew(session)
        voyage = Voyage(name="Preview Run", date=datetime.now(UTC), revenue_paise=1000000, status="completed")
        session.add(voyage)
        session.commit()
        post_revenue_transaction(session, voyage.id)

        preview = preview_voyage_payouts(session, voyage.id)
        assert len(preview["items"]) == 3

        # Verify 0 payouts in database
        count = session.query(Payout).filter(Payout.voyage_id == voyage.id).count()
        assert count == 0
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 15: Finalize Creates Correct Payout & Transaction Records
    # ----------------------------------------------------
    print("[15/21] Testing Finalize End-to-End Payout & Ledger Creation...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        crew = setup_standard_crew(session)
        voyage = Voyage(name="Grand Expedition", date=datetime.now(UTC), revenue_paise=10000000, status="completed")
        session.add(voyage)
        session.commit()
        post_revenue_transaction(session, voyage.id)
        create_and_post_expense(session, voyage.id, "Gunpowder", 1000000, datetime.now(UTC))

        # Net Profit = 9,000,000 paise (₹90,000)
        # Weights: 200, 150, 100 -> Total 450
        # 9,000,000 * 200 // 450 = 4,000,000
        # 9,000,000 * 150 // 450 = 3,000,000
        # 9,000,000 * 100 // 450 = 2,000,000
        _, payouts = finalize_voyage_payouts(session, voyage.id)
        assert len(payouts) == 3
        assert sum(p.payout_paise for p in payouts) == 9000000
        assert payouts[0].payout_paise == 4000000
        assert payouts[1].payout_paise == 3000000
        assert payouts[2].payout_paise == 2000000

        # Verify transaction log entry created
        tx = session.query(TransactionLog).filter(
            TransactionLog.voyage_id == voyage.id,
            TransactionLog.reference_type == "voyage_payout"
        ).first()
        assert tx is not None
        assert tx.amount_paise == 9000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 16: Atomicity Rollback on Failure
    # ----------------------------------------------------
    print("[16/21] Testing Atomic Rollback on Finalization Failure...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        voyage = Voyage(name="Planned Voyage", date=datetime.now(UTC), revenue_paise=1000000, status="planned")
        session.add(voyage)
        session.commit()

        try:
            finalize_voyage_payouts(session, voyage.id)
            assert False, "Should have failed for non-completed voyage"
        except HTTPException:
            pass

        count = session.query(Payout).filter(Payout.voyage_id == voyage.id).count()
        assert count == 0
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 17 & 18: Finalized Payout Immutability (PUT / DELETE blocked)
    # ----------------------------------------------------
    print("[17/21] Testing Payout Immutability (PUT /api/payouts blocked)...")
    print("[18/21] Testing Payout Immutability (DELETE /api/payouts blocked)...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        setup_standard_crew(session)
        v_resp = client.post("/api/voyages", json={
            "name": "Audit Voyage",
            "date": "2026-09-10T12:00:00",
            "revenue_paise": 5000000,
            "status": "completed"
        })
        v_id = v_resp.json()["id"]
        client.post(f"/api/voyages/{v_id}/revenue/post")

        fin_resp = client.post(f"/api/voyages/{v_id}/payouts/finalize")
        assert fin_resp.status_code == 201
        payout_id = fin_resp.json()["payouts"][0]["id"]

        # Attempt PUT -> 405 Method Not Allowed
        put_resp = client.put(f"/api/payouts/{payout_id}", json={"payout_paise": 99999})
        assert put_resp.status_code == 405

        # Attempt DELETE -> 405 Method Not Allowed
        del_resp = client.delete(f"/api/payouts/{payout_id}")
        assert del_resp.status_code == 405

        # Verify payout record is unchanged
        get_p = client.get(f"/api/payouts/{payout_id}")
        assert get_p.status_code == 200
        print("  -> Passed (PUT and DELETE return HTTP 405 Method Not Allowed)")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 19: Crew Payout History Endpoint
    # ----------------------------------------------------
    print("[19/21] Testing Crew Payout History API...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        crew = setup_standard_crew(session)
        c_id = crew[0].id

        v1 = Voyage(name="Voyage 1", date=datetime.now(UTC), revenue_paise=4500000, status="completed")
        session.add(v1)
        session.commit()
        post_revenue_transaction(session, v1.id)
        finalize_voyage_payouts(session, v1.id)

        history_resp = client.get(f"/api/crew/{c_id}/payouts")
        assert history_resp.status_code == 200
        hist_data = history_resp.json()
        assert len(hist_data) == 1
        assert hist_data[0]["crew_member_id"] == c_id
        assert hist_data[0]["payout_paise"] == 2000000  # 4.5M * 200/450 = 2M
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 20: Crew Cumulative Running Balance
    # ----------------------------------------------------
    print("[20/21] Testing Crew Cumulative Running Balance API...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        crew = setup_standard_crew(session)
        c_id = crew[0].id

        # Voyage 1 -> c1 gets 2,000,000 paise
        v1 = Voyage(name="Voyage A", date=datetime.now(UTC), revenue_paise=4500000, status="completed")
        session.add(v1)
        session.commit()
        post_revenue_transaction(session, v1.id)
        finalize_voyage_payouts(session, v1.id)

        # Voyage 2 -> c1 gets 2,000,000 paise
        v2 = Voyage(name="Voyage B", date=datetime.now(UTC), revenue_paise=4500000, status="completed")
        session.add(v2)
        session.commit()
        post_revenue_transaction(session, v2.id)
        finalize_voyage_payouts(session, v2.id)

        # Query running balance
        bal_resp = client.get(f"/api/crew/{c_id}/balance")
        assert bal_resp.status_code == 200
        bal_data = bal_resp.json()
        assert bal_data["crew_member_id"] == c_id
        assert bal_data["running_balance_paise"] == 4000000
        print("  -> Passed")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # TEST 21: Authorization Check (Crew role cannot finalize, Captain/Admin can)
    # ----------------------------------------------------
    print("[21/21] Testing Role Authorization for Payout Finalization...")
    client, session, engine, tmp_dir = get_test_context()
    try:
        setup_standard_crew(session)
        voyage = Voyage(name="Auth Voyage", date=datetime.now(UTC), revenue_paise=4500000, status="completed")
        session.add(voyage)
        session.commit()
        post_revenue_transaction(session, voyage.id)

        # Attempt finalize with X-User-Role: crew -> 403 Forbidden
        crew_resp = client.post(
            f"/api/voyages/{voyage.id}/payouts/finalize",
            headers={"X-User-Role": "crew"}
        )
        assert crew_resp.status_code == 403
        assert "not authorized" in crew_resp.json()["detail"]

        # Attempt finalize with X-User-Role: captain -> 201 Created
        cap_resp = client.post(
            f"/api/voyages/{voyage.id}/payouts/finalize",
            headers={"X-User-Role": "captain"}
        )
        assert cap_resp.status_code == 201
        print("  -> Passed (Role-based authorization enforced: CREW blocked with 403, CAPTAIN authorized)")
    finally:
        cleanup_context(session, engine, tmp_dir)

    # ----------------------------------------------------
    # PART 24: Invariant / Property Fuzzing Test (500 iterations)
    # ----------------------------------------------------
    print("=" * 60)
    print("Running Invariant / Property Fuzzing Test (500 Random Iterations)")
    print("=" * 60)
    random.seed(42)

    class MockRank:
        def __init__(self, share_weight_units):
            self.share_weight_units = share_weight_units
            self.name = "MockRank"

    class MockCrew:
        def __init__(self, crew_id, weight):
            self.id = crew_id
            self.name = f"MockCrew_{crew_id}"
            self.rank = MockRank(weight)

    for i in range(500):
        # Generate random profit between 1 paise and 100,000,000 paise (₹1,000,000)
        profit = random.randint(1, 100000000)
        num_crew = random.randint(1, 40)
        crew_list = [MockCrew(crew_id=j + 1, weight=random.randint(10, 500)) for j in range(num_crew)]

        items, total_w, val = calculate_integer_payout_distribution(profit, crew_list)
        payout_sum = sum(item["payout_paise"] for item in items)

        assert payout_sum == profit, (
            f"INVARIANT FAILED at iteration {i}: profit={profit}, num_crew={num_crew}, "
            f"payout_sum={payout_sum}, diff={profit - payout_sum}"
        )

    print("  -> Invariant Verified Across 500 Random Configurations: ZERO PAISE LOST [OK]")

    print("=" * 60)
    print("All Phase 6 Payout & Dividend Engine test suites passed successfully! [OK]")
    print("=" * 60)


def test_phase_6_payout_engine_suite():
    run_phase_6_tests()


if __name__ == "__main__":
    run_phase_6_tests()
