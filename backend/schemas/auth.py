"""
Pydantic schemas for Authentication, JWT Tokens, and User Management.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Payload for public user registration."""
    email: EmailStr = Field(..., description="Unique email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique pirate handle")
    password: str = Field(..., min_length=6, description="Account password (min 6 characters)")
    role: Optional[str] = Field(default=None, description="Requested role (untrusted, ignored in public signup)")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Username cannot be empty or whitespace only.")
        return cleaned


class UserLoginRequest(BaseModel):
    """Payload for credentials authentication."""
    email: str = Field(..., description="Registered email address or username")
    password: str = Field(..., min_length=1, description="Account password")


class UserPublicResponse(BaseModel):
    """Safe public representation of a user (no password hash)."""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class TokenResponse(BaseModel):
    """Authentication response payload containing JWT Bearer token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublicResponse


class UserStatusUpdate(BaseModel):
    """Payload for activating or deactivating a user."""
    is_active: bool


class UserRoleUpdate(BaseModel):
    """Payload for updating user authorization role."""
    role: str = Field(..., description="Must be ADMIN, CAPTAIN, or CREW")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"ADMIN", "CAPTAIN", "CREW"}
        val = v.strip().upper()
        if val not in allowed:
            raise ValueError(f"Role must be one of {allowed}, got '{v}'.")
        return val
