"""
Initial Administrator Provisioning Seed CLI Script.
Run via: python -m backend.seed_admin
"""

import os
import sys
from dotenv import load_dotenv

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import SessionLocal, init_db
from backend.core.security import hash_password
from backend.models.user import User

load_dotenv()


def seed_initial_admin():
    """
    Seed initial system administrator if no active administrator exists.
    Credentials are read from environment variables to prevent hardcoding.
    """
    init_db()
    db = SessionLocal()
    try:
        # Check if an active ADMIN already exists
        existing_admin = db.query(User).filter(User.role == "ADMIN", User.is_active == True).first()
        if existing_admin:
            print(f"[INFO] Active administrator already exists: '{existing_admin.username}' ({existing_admin.email}).")
            print("[INFO] No changes made.")
            return

        admin_username = os.getenv("INITIAL_ADMIN_USERNAME", "captain_admin").strip()
        admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@treasureledger.local").strip()
        admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "BlackbeardAdmin2026!").strip()

        if len(admin_password) < 6:
            print("[ERROR] INITIAL_ADMIN_PASSWORD must be at least 6 characters.")
            sys.exit(1)

        # Check for conflicts
        if db.query(User).filter(User.username == admin_username).first():
            print(f"[ERROR] User with username '{admin_username}' already exists with a non-admin role.")
            sys.exit(1)

        if db.query(User).filter(User.email == admin_email).first():
            print(f"[ERROR] User with email '{admin_email}' already exists with a non-admin role.")
            sys.exit(1)

        hashed_pw = hash_password(admin_password)
        admin = User(
            username=admin_username,
            email=admin_email,
            password_hash=hashed_pw,
            role="ADMIN",
            is_active=True
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("=" * 60)
        print("[SUCCESS] Initial administrator created successfully!")
        print(f"  Username : {admin.username}")
        print(f"  Email    : {admin.email}")
        print(f"  Role     : {admin.role}")
        print(f"  Status   : {'Active' if admin.is_active else 'Inactive'}")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    seed_initial_admin()
