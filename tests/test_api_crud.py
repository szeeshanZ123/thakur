"""
Integration Tests for Phase 4 Core CRUD API Layer.
Tests Ranks, Crew, Voyages, Expenses, Read-Only Transactions,
Pagination, Filters, Search, and Immutability Protections.
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.core.database import Base, get_db
from backend.models.rank import Rank
from backend.models.crew import CrewMember
from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog
from backend.models.payout import Payout


def get_test_client_and_session():
    """Sets up an isolated test database, overrides get_db dependency, and returns (client, session)."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test_api.db"
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
    return client, TestingSessionLocal(), engine, tmp_dir


# --- 1. Ranks API Tests ---

def test_ranks_crud_and_validation():
    client, session, engine, tmp_dir = get_test_client_and_session()
    try:
        # 1. Create Rank
        resp = client.post("/api/ranks", json={"name": "Captain", "share_weight_units": 200, "is_active": True})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Captain"
        assert data["share_weight_units"] == 200
        rank_id = data["id"]

        # 2. Duplicate rank name rejected
        resp_dup = client.post("/api/ranks", json={"name": "Captain", "share_weight_units": 180})
        assert resp_dup.status_code == 409

        # 3. Invalid zero/negative/float share weight rejected
        resp_zero = client.post("/api/ranks", json={"name": "Cook", "share_weight_units": 0})
        assert resp_zero.status_code == 422
        resp_float = client.post("/api/ranks", json={"name": "Cook", "share_weight_units": 1.5})
        assert resp_float.status_code == 422

        # 4. List ranks
        client.post("/api/ranks", json={"name": "First Mate", "share_weight_units": 150})
        resp_list = client.get("/api/ranks")
        assert resp_list.status_code == 200
        ranks = resp_list.json()
        assert len(ranks) == 2
        assert ranks[0]["share_weight_units"] >= ranks[1]["share_weight_units"]  # Ordered desc

        # 5. Get rank by ID
        resp_get = client.get(f"/api/ranks/{rank_id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["id"] == rank_id

        # 6. Update rank
        resp_put = client.put(f"/api/ranks/{rank_id}", json={"share_weight_units": 220})
        assert resp_put.status_code == 200
        assert resp_put.json()["share_weight_units"] == 220

        # 7. Create crew member referencing rank and test safe deactivation on delete
        resp_crew = client.post("/api/crew", json={"name": "Blackbeard", "rank_id": rank_id})
        assert resp_crew.status_code == 201

        # Delete rank with crew -> should soft deactivate (is_active=False)
        resp_del = client.delete(f"/api/ranks/{rank_id}")
        assert resp_del.status_code == 200
        assert resp_del.json()["is_active"] is False

    finally:
        session.close()
        engine.dispose()


# --- 2. Crew API Tests ---

def test_crew_crud_search_and_filters():
    client, session, engine, tmp_dir = get_test_client_and_session()
    try:
        # Create ranks
        r1 = client.post("/api/ranks", json={"name": "Captain", "share_weight_units": 200}).json()["id"]
        r2 = client.post("/api/ranks", json={"name": "Gunner", "share_weight_units": 120}).json()["id"]

        # 1. Create Crew
        resp_c1 = client.post("/api/crew", json={"name": "Jack Sparrow", "rank_id": r1})
        assert resp_c1.status_code == 201
        c1_id = resp_c1.json()["id"]
        assert resp_c1.json()["rank_name"] == "Captain"
        assert resp_c1.json()["share_weight_units"] == 200

        client.post("/api/crew", json={"name": "Hector Barbossa", "rank_id": r1})
        client.post("/api/crew", json={"name": "Will Turner", "rank_id": r2})

        # 2. Invalid rank ID rejected
        resp_bad_rank = client.post("/api/crew", json={"name": "Ghost", "rank_id": 9999})
        assert resp_bad_rank.status_code == 404

        # 3. List crew with search and pagination
        resp_search = client.get("/api/crew?search=Jack")
        assert resp_search.status_code == 200
        search_data = resp_search.json()
        assert search_data["total"] == 1
        assert search_data["items"][0]["name"] == "Jack Sparrow"

        # 4. Filter by rank_id
        resp_rank_filter = client.get(f"/api/crew?rank_id={r1}")
        assert resp_rank_filter.json()["total"] == 2

        # 5. Soft-deactivate crew member
        resp_del = client.delete(f"/api/crew/{c1_id}")
        assert resp_del.status_code == 200
        assert resp_del.json()["is_active"] is False

        # Filter active crew only
        resp_active = client.get("/api/crew?is_active=true")
        assert resp_active.json()["total"] == 2

        # 6. Check ledger endpoint
        resp_ledger = client.get(f"/api/crew/{c1_id}/ledger")
        assert resp_ledger.status_code == 200
        assert isinstance(resp_ledger.json(), list)

    finally:
        session.close()
        engine.dispose()


# --- 3. Voyage API Tests ---

def test_voyages_crud_and_deletion_safety():
    client, session, engine, tmp_dir = get_test_client_and_session()
    try:
        # 1. Create Voyage (e.g. ₹50,000 gross revenue = 5000000 paise)
        v_payload = {
            "name": "Tortuga Raid",
            "date": "2026-09-10T10:00:00",
            "description": "Spanish merchant fleet intercept",
            "revenue_paise": 5000000,
            "status": "completed"
        }
        resp_v = client.post("/api/voyages", json=v_payload)
        assert resp_v.status_code == 201
        v_id = resp_v.json()["id"]
        assert resp_v.json()["revenue_paise"] == 5000000

        # 2. Rejection of negative or float revenue
        resp_neg = client.post("/api/voyages", json={**v_payload, "revenue_paise": -500})
        assert resp_neg.status_code == 422
        resp_flt = client.post("/api/voyages", json={**v_payload, "revenue_paise": 500.75})
        assert resp_flt.status_code == 422

        # 3. Add expense to voyage
        client.post("/api/expenses", json={
            "voyage_id": v_id,
            "category": "Ship Repair",
            "amount_paise": 1000000
        })

        # 4. Get voyage details (checks calculated expense and net profit)
        resp_get = client.get(f"/api/voyages/{v_id}")
        assert resp_get.status_code == 200
        v_data = resp_get.json()
        assert v_data["total_expenses_paise"] == 1000000
        assert v_data["net_profit_paise"] == 4000000
        assert v_data["profit_margin_basis_points"] == 8000  # 80.00%

        # 5. Delete voyage with expenses should be BLOCKED (409 Conflict)
        resp_del_blocked = client.delete(f"/api/voyages/{v_id}")
        assert resp_del_blocked.status_code == 409
        assert "financial records" in resp_del_blocked.json()["detail"]

        # 6. Delete empty voyage should SUCCEED
        empty_v = client.post("/api/voyages", json={
            "name": "Empty Voyage",
            "date": "2026-09-11T12:00:00",
            "revenue_paise": 0,
            "status": "planned"
        }).json()["id"]
        resp_del_empty = client.delete(f"/api/voyages/{empty_v}")
        assert resp_del_empty.status_code == 200

    finally:
        session.close()
        engine.dispose()


# --- 4. Expenses API Tests ---

def test_expenses_crud_and_validation():
    client, session, engine, tmp_dir = get_test_client_and_session()
    try:
        # Create Voyage
        v_id = client.post("/api/voyages", json={
            "name": "Caribbean Patrol",
            "date": "2026-09-10T10:00:00",
            "revenue_paise": 2000000,
            "status": "ongoing"
        }).json()["id"]

        # 1. Create Expense
        resp_exp = client.post("/api/expenses", json={
            "voyage_id": v_id,
            "category": "Gunpowder",
            "amount_paise": 300000,
            "description": "5 powder kegs"
        })
        assert resp_exp.status_code == 201
        exp_id = resp_exp.json()["id"]
        assert resp_exp.json()["amount_paise"] == 300000

        # 2. Invalid voyage ID rejected
        resp_bad_v = client.post("/api/expenses", json={
            "voyage_id": 9999,
            "category": "Rum",
            "amount_paise": 50000
        })
        assert resp_bad_v.status_code == 404

        # 3. List expenses with filters
        resp_list = client.get(f"/api/expenses?voyage_id={v_id}&category=Gunpowder")
        assert resp_list.status_code == 200
        assert resp_list.json()["total"] == 1

        # 4. Attempting to update or delete a POSTED expense is BLOCKED (409 Conflict)
        resp_put_blocked = client.put(f"/api/expenses/{exp_id}", json={"amount_paise": 350000})
        assert resp_put_blocked.status_code == 409
        assert "Posted" in resp_put_blocked.json()["detail"]

        resp_del_blocked = client.delete(f"/api/expenses/{exp_id}")
        assert resp_del_blocked.status_code == 409
        assert "Posted" in resp_del_blocked.json()["detail"]

        # 5. Unposted expense can still be updated and deleted
        unposted_exp = Expense(
            voyage_id=v_id,
            category="Rations",
            amount_paise=50000,
            date=datetime.utcnow(),
            description="Draft ration order"
        )
        session.add(unposted_exp)
        session.commit()
        session.refresh(unposted_exp)

        resp_put = client.put(f"/api/expenses/{unposted_exp.id}", json={"amount_paise": 60000})
        assert resp_put.status_code == 200
        assert resp_put.json()["amount_paise"] == 60000

        resp_del = client.delete(f"/api/expenses/{unposted_exp.id}")
        assert resp_del.status_code == 200


    finally:
        session.close()
        engine.dispose()


# --- 5. Transactions Read-Only & Immutability Tests ---

def test_transactions_read_only_and_immutability():
    client, session, engine, tmp_dir = get_test_client_and_session()
    try:
        # Create Voyage and insert a TransactionLog directly via ORM to test read endpoints
        v = Voyage(name="Treasure Island", date=datetime.utcnow(), revenue_paise=1000000, status="completed")
        session.add(v)
        session.commit()

        tx1 = TransactionLog(
            voyage_id=v.id,
            transaction_type="CREDIT",
            amount_paise=1000000,
            description="Loot revenue",
            timestamp=datetime.utcnow()
        )
        tx2 = TransactionLog(
            voyage_id=v.id,
            transaction_type="DEBIT",
            amount_paise=200000,
            description="Vessel repairs",
            timestamp=datetime.utcnow()
        )
        session.add_all([tx1, tx2])
        session.commit()

        # 1. GET /api/transactions
        resp_list = client.get("/api/transactions")
        assert resp_list.status_code == 200
        assert resp_list.json()["total"] == 2

        # 2. GET /api/transactions/{id}
        resp_get = client.get(f"/api/transactions/{tx1.id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["transaction_type"] == "CREDIT"

        # 3. GET /api/transactions/voyage/{voyage_id}
        resp_voyage_tx = client.get(f"/api/transactions/voyage/{v.id}")
        assert resp_voyage_tx.status_code == 200
        assert len(resp_voyage_tx.json()) == 2

        # 4. IMMUTABILITY CHECK: PUT and DELETE endpoints must return 405 Method Not Allowed
        resp_put = client.put(f"/api/transactions/{tx1.id}", json={"amount_paise": 500})
        assert resp_put.status_code == 405  # Method Not Allowed

        resp_del = client.delete(f"/api/transactions/{tx1.id}")
        assert resp_del.status_code == 405  # Method Not Allowed

    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Running Phase 4 Core CRUD APIs Test Suite")
    print("=" * 60)

    print("[1/5] Testing Ranks CRUD & Share Weight Validations...")
    test_ranks_crud_and_validation()
    print("  -> Passed")

    print("[2/5] Testing Crew CRUD, Search, Filters & Ledger...")
    test_crew_crud_search_and_filters()
    print("  -> Passed")

    print("[3/5] Testing Voyages CRUD & Financial Deletion Safety...")
    test_voyages_crud_and_deletion_safety()
    print("  -> Passed")

    print("[4/5] Testing Expenses CRUD & Validation...")
    test_expenses_crud_and_validation()
    print("  -> Passed")

    print("[5/5] Testing Transaction Read-Only APIs & Immutability (405 on PUT/DELETE)...")
    test_transactions_read_only_and_immutability()
    print("  -> Passed")

    print("=" * 60)
    print("All 5 Phase 4 Core CRUD API test suites passed successfully! [OK]")
    print("=" * 60)
