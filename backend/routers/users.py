"""
User Management API Router (Administrator Only).
Handles listing users, retrieving user details, updating user status, and role assignments.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.user import User
from backend.schemas.auth import (
    UserPublicResponse,
    UserStatusUpdate,
    UserRoleUpdate,
)
from backend.dependencies.auth import require_admin

router = APIRouter(prefix="/api/users", tags=["User Management"])


@router.get("", response_model=List[UserPublicResponse], summary="List all users (Admin only)")
def list_users(
    role: Optional[str] = Query(None, description="Filter by role (ADMIN, CAPTAIN, CREW)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Retrieve all system users with optional role and status filters."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.upper())
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    return query.order_by(User.id.asc()).all()


@router.get("/{user_id}", response_model=UserPublicResponse, summary="Get user by ID (Admin only)")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Retrieve details for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    return user


@router.patch("/{user_id}/status", response_model=UserPublicResponse, summary="Update user active status (Admin only)")
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Activate or deactivate a user account.
    Safety Guard: Prevents deactivating the last active ADMIN.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    # Protect last active ADMIN from accidental deactivation
    if target_user.role == "ADMIN" and not payload.is_active:
        active_admin_count = (
            db.query(User)
            .filter(User.role == "ADMIN", User.is_active == True, User.id != target_user.id)
            .count()
        )
        if active_admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last remaining active administrator."
            )

    target_user.is_active = payload.is_active
    db.commit()
    db.refresh(target_user)
    return target_user


@router.patch("/{user_id}/role", response_model=UserPublicResponse, summary="Update user role (Admin only)")
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Update a user's role (ADMIN, CAPTAIN, CREW).
    Restrictions:
    - Only administrators can access this endpoint.
    - Administrators cannot alter their own role (prevents accidental self-demotion or self-promotion).
    - Cannot demote the last remaining active administrator.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    # A user cannot change their own role
    if admin_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot modify their own role."
        )

    # Protect last remaining active ADMIN from demotion
    if target_user.role == "ADMIN" and payload.role != "ADMIN":
        active_admin_count = (
            db.query(User)
            .filter(User.role == "ADMIN", User.is_active == True, User.id != target_user.id)
            .count()
        )
        if active_admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last remaining active administrator."
            )

    target_user.role = payload.role
    db.commit()
    db.refresh(target_user)
    return target_user
