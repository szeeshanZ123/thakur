# Captain's Treasure Ledger — Authentication & RBAC API Contract

This document provides the frontend integration contract for Authentication and Role-Based Access Control (RBAC).

---

## 1. Authentication Standard

All authenticated requests must include the JWT access token in the standard HTTP `Authorization` header:

```http
Authorization: Bearer <access_token>
```

Tokens are stateless JSON Web Tokens (JWT) signed with `HS256`.

---

## 2. Roles & Permissions Hierarchy

| Role | Scope | Permitted Operations |
|---|---|---|
| `CREW` | Read-only / Self | View ranks, view crew, view voyages, view expenses, view transactions, view own dividend ledger, invoke AI/ML inference |
| `CAPTAIN` | Operational Leadership | All `CREW` permissions plus create/update ranks, enroll/update crew, log/update voyages, record/update expenses, train ML models |
| `ADMIN` | System Administration | All `CAPTAIN` permissions plus user management, activation/deactivation, and role assignment |

---

## 3. Endpoints Specification

### A. Public Registration

* **Endpoint:** `POST /api/auth/register`
* **Access:** Public (No token required)
* **Description:** Creates a new account. Untrusted client input cannot self-grant privileged roles; all public registrations are assigned `CREW`.

#### Request Body
```json
{
  "email": "sailor@blackpearl.sea",
  "username": "will_turner",
  "password": "SecretPassword123"
}
```

#### Response Body (201 Created)
```json
{
  "id": 2,
  "username": "will_turner",
  "email": "sailor@blackpearl.sea",
  "role": "CREW",
  "is_active": true,
  "created_at": "2026-09-11T12:00:00",
  "last_login_at": null
}
```

#### Error Responses
* `400 / 422`: Validation error (password too short, invalid email format, empty username).
* `409 Conflict`: `{"detail": "An account with this email address already exists."}` or `{"detail": "A pirate with this handle is already registered."}`

---

### B. User Login

* **Endpoint:** `POST /api/auth/login`
* **Access:** Public (No token required)
* **Description:** Verifies credentials, updates `last_login_at`, and returns a JWT access token. Accepts either registered email or username in the `email` field.

#### Request Body
```json
{
  "email": "sailor@blackpearl.sea",
  "password": "SecretPassword123"
}
```

#### Response Body (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 2,
    "username": "will_turner",
    "email": "sailor@blackpearl.sea",
    "role": "CREW",
    "is_active": true,
    "created_at": "2026-09-11T12:00:00",
    "last_login_at": "2026-09-11T12:05:00"
  }
}
```

#### Error Responses
* `401 Unauthorized`: `{"detail": "Invalid credentials."}` (Generic error; does not disclose user existence).
* `403 Forbidden`: `{"detail": "Inactive user account."}`

---

### C. Current User Profile

* **Endpoint:** `GET /api/auth/me`
* **Access:** Authenticated (Any active user with valid token)
* **Header:** `Authorization: Bearer <access_token>`

#### Response Body (200 OK)
```json
{
  "id": 2,
  "username": "will_turner",
  "email": "sailor@blackpearl.sea",
  "role": "CREW",
  "is_active": true,
  "created_at": "2026-09-11T12:00:00",
  "last_login_at": "2026-09-11T12:05:00"
}
```

#### Error Responses
* `401 Unauthorized`: Missing, expired, or invalid token.
* `403 Forbidden`: Account deactivated.

---

### D. Logout

* **Endpoint:** `POST /api/auth/logout`
* **Access:** Authenticated
* **Header:** `Authorization: Bearer <access_token>`
* **Description:** Advises the client to delete the stored JWT.

#### Response Body (200 OK)
```json
{
  "message": "Successfully logged out. Please discard the access token.",
  "status": "success",
  "username": "will_turner"
}
```

---

### E. User Management (Admin Only)

#### 1. List Users
* **Endpoint:** `GET /api/users`
* **Query Params:** `?role=CAPTAIN&is_active=true`
* **Access:** `ADMIN` only

#### 2. Get User
* **Endpoint:** `GET /api/users/{id}`
* **Access:** `ADMIN` only

#### 3. Update User Status
* **Endpoint:** `PATCH /api/users/{id}/status`
* **Access:** `ADMIN` only
* **Body:** `{"is_active": false}`
* **Protection:** Cannot deactivate the last remaining active administrator.

#### 4. Update User Role
* **Endpoint:** `PATCH /api/users/{id}/role`
* **Access:** `ADMIN` only
* **Body:** `{"role": "CAPTAIN"}`
* **Restrictions:**
  - Administrators cannot alter their own role.
  - Cannot demote the last remaining active administrator.

---

## 4. Protected Ledger Routes Summary

| Endpoint | Method | Required Role | Notes |
|---|---|---|---|
| `/health` | `GET` | Public | Status monitoring |
| `/api/ranks` | `GET` | `CREW`+ | List ranks |
| `/api/ranks` | `POST` | `CAPTAIN`+ | Create rank |
| `/api/ranks/{id}` | `PUT`, `DELETE` | `CAPTAIN`+ | Modify rank |
| `/api/crew` | `GET` | `CREW`+ | List crew |
| `/api/crew` | `POST` | `CAPTAIN`+ | Enroll crew |
| `/api/crew/{id}` | `PUT`, `DELETE` | `CAPTAIN`+ | Update/deactivate crew |
| `/api/crew/{id}/ledger` | `GET` | `CREW`+ | View dividend history |
| `/api/voyages` | `GET` | `CREW`+ | List voyages |
| `/api/voyages` | `POST`, `PUT`, `DELETE` | `CAPTAIN`+ | Manage voyages |
| `/api/expenses` | `GET` | `CREW`+ | List expenses |
| `/api/expenses` | `POST`, `PUT`, `DELETE` | `CAPTAIN`+ | Manage expenses |
| `/api/transactions` | `GET` | `CREW`+ | Read audit log (immutable) |
| `/api/ai/generate` | `POST` | `CREW`+ | AI assistant prompt |
| `/api/ml/predict` | `POST` | `CREW`+ | ML inference |
| `/api/ml/train` | `POST` | `CAPTAIN`+ | Retrain baseline model |
| `/api/users/*` | `GET`, `PATCH` | `ADMIN` | User administration |
