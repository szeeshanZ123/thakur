"""
Authentication API Router.
Handles user registration, login, profile retrieval, and logout.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.core.database import get_db
from backend.core.security import hash_password, verify_password, create_access_token
from backend.models.user import User
from backend.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserPublicResponse,
    TokenResponse,
)
from backend.dependencies.auth import get_current_active_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserPublicResponse, status_code=status.HTTP_201_CREATED, summary="Register new user")
def register_user(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Public registration endpoint.
    Public signups are strictly granted the CREW role by default.
    Privileged roles cannot be self-assigned.
    """
    # Check for duplicate email
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )

    # Check for duplicate username
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pirate with this handle is already registered."
        )

    # Hash password securely with bcrypt
    hashed = hash_password(payload.password)

    # Enforce default CREW role for public registration
    new_user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hashed,
        role="CREW",
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse, summary="User login")
def login_user(
    payload: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user via email/username and password.
    Returns signed JWT access token and user metadata.
    """
    user = (
        db.query(User)
        .filter((User.email == payload.email) | (User.username == payload.email))
        .first()
    )

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account."
        )

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublicResponse.model_validate(user)
    )


@router.get("/me", response_model=UserPublicResponse, summary="Get current authenticated user")
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve profile details of the currently authenticated active user.
    """
    return current_user


@router.post("/logout", summary="Logout authenticated user")
def logout_user(
    current_user: User = Depends(get_current_active_user)
):
    """
    Stateless JWT logout strategy:
    Tokens are short-lived/session-scoped. The server advises the client
    to immediately delete and invalidate the Bearer token locally.
    """
    return {
        "message": "Successfully logged out. Please discard the access token.",
        "status": "success",
        "username": current_user.username
    }
