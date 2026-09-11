"""
Comprehensive Authentication & RBAC Test Suite
for Captain's Treasure Ledger.

Strategy
--------
* An in-memory SQLite DB with ``StaticPool`` is used so all SQLAlchemy
  sessions share the SAME underlying connection -- preventing the
  ``no such table`` error that occurs with per-connection in-memory DBs.
* The FastAPI ``get_db`` dependency is overridden before the TestClient
  (and its startup event) runs.
* All ORM models are imported via ``backend.models`` so every table is
  registered in ``Base.metadata`` before ``create_all`` is called.
* The TestClient is used as a context manager to trigger startup/shutdown.
"""

import os
import sys
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ALL models so Base.metadata knows about every table
import backend.models  # noqa: F401

from backend.core.database import Base, get_db
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.main import app
from backend.models.user import User

# ---------------------------------------------------------------------------
# In-memory SQLite with StaticPool -- single shared connection for all tests
# ---------------------------------------------------------------------------
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
def _setup_db():
    """Create schema and install DB override for the entire test session."""
    Base.metadata.create_all(bind=_engine)
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="session")
def client(_setup_db):
    """One TestClient (with lifeycle) shared by the entire test session."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reg(suffix: str, password: str = "secret123") -> dict:
    return {
        "email": f"{suffix}@treasure.test",
        "username": f"pirate_{suffix}",
        "password": password,
    }


def _login(c: TestClient, identifier: str, password: str = "secret123") -> str:
    resp = c.post("/api/auth/login", json={"email": identifier, "password": password})
    assert resp.status_code == 200, f"Login failed for '{identifier}': {resp.json()}"
    return resp.json()["access_token"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _db_add_user(username: str, email: str, password: str, role: str) -> None:
    """Insert a user directly into the test DB (bypasses the HTTP layer)."""
    db = _Session()
    if not db.query(User).filter(User.email == email).first():
        db.add(User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        ))
        db.commit()
    db.close()


# ---------------------------------------------------------------------------
# 1. Security core
# ---------------------------------------------------------------------------

class TestSecurityCore:

    def test_hash_produces_different_salts(self):
        assert hash_password("pirate") != hash_password("pirate")

    def test_verify_correct_password(self):
        h = hash_password("treasure")
        assert verify_password("treasure", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("treasure")
        assert verify_password("nope", h) is False

    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "42", "role": "CAPTAIN"})
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "CAPTAIN"

    def test_expired_token_raises(self):
        import jwt as pyjwt
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_tampered_token_raises(self):
        import jwt as pyjwt
        token = create_access_token({"sub": "1"})
        with pytest.raises(pyjwt.PyJWTError):
            decode_access_token(token[:-4] + "XXXX")


# ---------------------------------------------------------------------------
# 2. Registration
# ---------------------------------------------------------------------------

class TestRegister:

    def test_happy_path(self, client):
        resp = client.post("/api/auth/register", json=_reg("alpha"))
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "alpha@treasure.test"
        assert data["username"] == "pirate_alpha"
        assert data["role"] == "CREW", "Public signup must always yield CREW"
        assert data["is_active"] is True
        assert "id" in data and "created_at" in data

    def test_no_password_hash_in_response(self, client):
        resp = client.post("/api/auth/register", json=_reg("beta"))
        assert resp.status_code == 201
        body = resp.json()
        assert "password" not in body and "password_hash" not in body

    def test_duplicate_email_409(self, client):
        payload = _reg("gamma")
        client.post("/api/auth/register", json=payload)
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409
        assert "email" in resp.json()["detail"].lower()

    def test_duplicate_username_409(self, client):
        client.post("/api/auth/register", json={"email": "u1@test.com", "username": "shared_handle", "password": "pass123"})
        resp = client.post("/api/auth/register", json={"email": "u2@test.com", "username": "shared_handle", "password": "pass123"})
        assert resp.status_code == 409
        assert "pirate" in resp.json()["detail"].lower()

    def test_short_password_422(self, client):
        resp = client.post("/api/auth/register", json={"email": "s@s.com", "username": "shorty99", "password": "abc"})
        assert resp.status_code == 422

    def test_short_username_422(self, client):
        resp = client.post("/api/auth/register", json={"email": "sn@sn.com", "username": "ab", "password": "password123"})
        assert resp.status_code == 422

    def test_invalid_email_422(self, client):
        resp = client.post("/api/auth/register", json={"email": "not-an-email", "username": "validname9", "password": "password123"})
        assert resp.status_code == 422

    def test_role_self_promotion_blocked(self, client):
        """Attacker cannot self-promote to ADMIN via the register endpoint."""
        payload = {**_reg("attacker"), "role": "ADMIN"}
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 201
        assert resp.json()["role"] == "CREW"


# ---------------------------------------------------------------------------
# 3. Login
# ---------------------------------------------------------------------------

class TestLogin:

    @pytest.fixture(autouse=True, scope="class")
    def seed(self, client):
        client.post("/api/auth/register", json=_reg("logintest"))

    def test_happy_path(self, client):
        resp = client.post("/api/auth/login", json={"email": "logintest@treasure.test", "password": "secret123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["email"] == "logintest@treasure.test"

    def test_login_via_username(self, client):
        resp = client.post("/api/auth/login", json={"email": "pirate_logintest", "password": "secret123"})
        assert resp.status_code == 200

    def test_wrong_password_401(self, client):
        resp = client.post("/api/auth/login", json={"email": "logintest@treasure.test", "password": "wrongpass"})
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]

    def test_nonexistent_user_401(self, client):
        resp = client.post("/api/auth/login", json={"email": "ghost@nowhere.com", "password": "x"})
        assert resp.status_code == 401

    def test_inactive_user_403(self, client):
        db = _Session()
        user = db.query(User).filter(User.email == "logintest@treasure.test").first()
        user.is_active = False
        db.commit()
        db.close()

        resp = client.post("/api/auth/login", json={"email": "logintest@treasure.test", "password": "secret123"})
        assert resp.status_code == 403

        db = _Session()
        user = db.query(User).filter(User.email == "logintest@treasure.test").first()
        user.is_active = True
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# 4. GET /api/auth/me
# ---------------------------------------------------------------------------

class TestMe:

    @pytest.fixture(autouse=True, scope="class")
    def seed(self, client):
        client.post("/api/auth/register", json=_reg("metest"))

    def test_valid_token(self, client):
        token = _login(client, "metest@treasure.test")
        resp = client.get("/api/auth/me", headers=_bearer(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "metest@treasure.test"
        assert "password_hash" not in resp.json()

    def test_no_token_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_invalid_token_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer totallyfake"})
        assert resp.status_code == 401

    def test_expired_token_401(self, client):
        expired = create_access_token({"sub": "9999", "role": "CREW"}, expires_delta=timedelta(seconds=-10))
        assert client.get("/api/auth/me", headers=_bearer(expired)).status_code == 401


# ---------------------------------------------------------------------------
# 5. POST /api/auth/logout
# ---------------------------------------------------------------------------

class TestLogout:

    @pytest.fixture(autouse=True, scope="class")
    def seed(self, client):
        client.post("/api/auth/register", json=_reg("logouttest"))

    def test_authenticated_logout(self, client):
        token = _login(client, "logouttest@treasure.test")
        resp = client.post("/api/auth/logout", headers=_bearer(token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert resp.json()["username"] == "pirate_logouttest"

    def test_no_token_returns_401(self, client):
        assert client.post("/api/auth/logout").status_code == 401


# ---------------------------------------------------------------------------
# 6. User management  (Admin-only routes)
# ---------------------------------------------------------------------------

class TestUserManagement:

    @pytest.fixture(autouse=True, scope="class")
    def seed(self, client):
        _db_add_user("admin_master", "admin@treasure.test", "adminpass", "ADMIN")
        client.post("/api/auth/register", json=_reg("crew_a"))
        client.post("/api/auth/register", json=_reg("crew_b"))

    @pytest.fixture(scope="class")
    def admin_tok(self, client):
        return _login(client, "admin@treasure.test", "adminpass")

    @pytest.fixture(scope="class")
    def crew_tok(self, client):
        return _login(client, "crew_a@treasure.test")

    def test_admin_lists_users(self, client, admin_tok):
        resp = client.get("/api/users", headers=_bearer(admin_tok))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_crew_cannot_list_users_403(self, client, crew_tok):
        assert client.get("/api/users", headers=_bearer(crew_tok)).status_code == 403

    def test_no_token_list_401(self, client):
        assert client.get("/api/users").status_code == 401

    def test_role_filter(self, client, admin_tok):
        resp = client.get("/api/users?role=CREW", headers=_bearer(admin_tok))
        assert resp.status_code == 200
        assert all(u["role"] == "CREW" for u in resp.json())

    def test_get_user_by_id(self, client, admin_tok):
        uid = client.get("/api/users", headers=_bearer(admin_tok)).json()[0]["id"]
        resp = client.get(f"/api/users/{uid}", headers=_bearer(admin_tok))
        assert resp.status_code == 200
        assert resp.json()["id"] == uid

    def test_get_nonexistent_user_404(self, client, admin_tok):
        assert client.get("/api/users/999999", headers=_bearer(admin_tok)).status_code == 404

    def test_deactivate_crew_user(self, client, admin_tok):
        crew_users = client.get("/api/users?role=CREW", headers=_bearer(admin_tok)).json()
        tid = crew_users[0]["id"]
        resp = client.patch(f"/api/users/{tid}/status", json={"is_active": False}, headers=_bearer(admin_tok))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_cannot_deactivate_last_admin(self, client, admin_tok):
        admin_id = client.get("/api/auth/me", headers=_bearer(admin_tok)).json()["id"]
        resp = client.patch(f"/api/users/{admin_id}/status", json={"is_active": False}, headers=_bearer(admin_tok))
        assert resp.status_code == 400
        assert "last remaining" in resp.json()["detail"].lower()

    def test_promote_crew_to_captain(self, client, admin_tok):
        crew_users = [u for u in client.get("/api/users?role=CREW", headers=_bearer(admin_tok)).json() if u["is_active"]]
        if not crew_users:
            pytest.skip("No active CREW user available for promotion")
        resp = client.patch(f"/api/users/{crew_users[0]['id']}/role", json={"role": "CAPTAIN"}, headers=_bearer(admin_tok))
        assert resp.status_code == 200
        assert resp.json()["role"] == "CAPTAIN"

    def test_admin_cannot_change_own_role(self, client, admin_tok):
        admin_id = client.get("/api/auth/me", headers=_bearer(admin_tok)).json()["id"]
        resp = client.patch(f"/api/users/{admin_id}/role", json={"role": "CAPTAIN"}, headers=_bearer(admin_tok))
        assert resp.status_code == 400
        assert "own role" in resp.json()["detail"].lower()

    def test_invalid_role_422(self, client, admin_tok):
        uid = client.get("/api/users", headers=_bearer(admin_tok)).json()[0]["id"]
        resp = client.patch(f"/api/users/{uid}/role", json={"role": "PIRATE_KING"}, headers=_bearer(admin_tok))
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 7. RBAC enforcement on business routers
# ---------------------------------------------------------------------------

class TestRBAC:

    @pytest.fixture(autouse=True, scope="class")
    def seed(self, client):
        _db_add_user("rbac_crew",    "rbac_crew@test.com",    "pass", "CREW")
        _db_add_user("rbac_captain", "rbac_captain@test.com", "pass", "CAPTAIN")
        _db_add_user("rbac_admin",   "rbac_admin@test.com",   "pass", "ADMIN")

    @pytest.fixture(scope="class")
    def crew_tok(self, client):
        return _login(client, "rbac_crew@test.com", "pass")

    @pytest.fixture(scope="class")
    def captain_tok(self, client):
        return _login(client, "rbac_captain@test.com", "pass")

    @pytest.fixture(scope="class")
    def admin_tok(self, client):
        return _login(client, "rbac_admin@test.com", "pass")

    # --- Ranks (crew+ read / captain+ write) ---
    def test_crew_can_read_ranks(self, client, crew_tok):
        assert client.get("/api/ranks", headers=_bearer(crew_tok)).status_code == 200

    def test_captain_can_read_ranks(self, client, captain_tok):
        assert client.get("/api/ranks", headers=_bearer(captain_tok)).status_code == 200

    def test_no_token_ranks_401(self, client):
        assert client.get("/api/ranks").status_code == 401

    def test_crew_cannot_create_rank_403(self, client, crew_tok):
        resp = client.post("/api/ranks", json={"name": "Powder Monkey", "share_weight_units": 50}, headers=_bearer(crew_tok))
        assert resp.status_code == 403

    def test_captain_can_create_rank(self, client, captain_tok):
        resp = client.post("/api/ranks", json={"name": "Lookout", "share_weight_units": 60}, headers=_bearer(captain_tok))
        assert resp.status_code == 201

    # --- Voyages ---
    def test_crew_can_read_voyages(self, client, crew_tok):
        assert client.get("/api/voyages", headers=_bearer(crew_tok)).status_code == 200

    def test_no_token_voyages_401(self, client):
        assert client.get("/api/voyages").status_code == 401

    def test_crew_cannot_create_voyage_403(self, client, crew_tok):
        from datetime import datetime
        resp = client.post(
            "/api/voyages",
            json={"name": "Ghost Ship Run", "date": datetime.utcnow().isoformat(), "revenue_paise": 500000},
            headers=_bearer(crew_tok),
        )
        assert resp.status_code == 403

    def test_captain_can_create_voyage(self, client, captain_tok):
        from datetime import datetime
        resp = client.post(
            "/api/voyages",
            json={"name": "Blackbeard Route", "date": datetime.utcnow().isoformat(), "revenue_paise": 1_000_000},
            headers=_bearer(captain_tok),
        )
        assert resp.status_code == 201

    # --- Expenses ---
    def test_crew_can_read_expenses(self, client, crew_tok):
        assert client.get("/api/expenses", headers=_bearer(crew_tok)).status_code == 200

    def test_no_token_expenses_401(self, client):
        assert client.get("/api/expenses").status_code == 401

    # --- Transactions ---
    def test_crew_can_read_transactions(self, client, crew_tok):
        assert client.get("/api/transactions", headers=_bearer(crew_tok)).status_code == 200

    def test_no_token_transactions_401(self, client):
        assert client.get("/api/transactions").status_code == 401
