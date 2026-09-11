"""
Pydantic schemas for Rank validation and serialization.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class RankBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Unique rank title (e.g., Captain, Quartermaster)")
    share_weight_units: int = Field(..., strict=True, gt=0, description="Integer share weight units (e.g., 200 = 2.0x, 100 = 1.0x)")
    is_active: bool = Field(default=True, description="Whether the rank is currently active")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Rank name cannot be empty or whitespace only")
        return trimmed


class RankCreate(RankBase):
    """Request payload for creating a new pirate rank."""
    pass


class RankUpdate(BaseModel):
    """Request payload for updating an existing pirate rank."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    share_weight_units: Optional[int] = Field(None, strict=True, gt=0)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Rank name cannot be empty or whitespace only")
            return trimmed
        return v


class RankResponse(RankBase):
    """Response model for a pirate rank."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
