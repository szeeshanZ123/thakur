"""
Pydantic schemas for CrewMember validation and serialization.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class CrewBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Pirate full name or alias")
    rank_id: int = Field(..., strict=True, gt=0, description="Foreign key reference to Rank ID")
    is_active: bool = Field(default=True, description="Whether the pirate is active aboard the vessel")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Crew member name cannot be empty or whitespace only")
        return trimmed


class CrewCreate(CrewBase):
    """Request payload for enrolling a new crew member."""
    pass


class CrewUpdate(BaseModel):
    """Request payload for updating crew member details or toggling status."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    rank_id: Optional[int] = Field(None, strict=True, gt=0)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Crew member name cannot be empty or whitespace only")
            return trimmed
        return v


class CrewResponse(BaseModel):
    """Response model for a crew member with joined rank details."""
    id: int
    name: str
    rank_id: int
    rank_name: Optional[str] = None
    share_weight_units: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CrewSummary(BaseModel):
    """Lightweight summary model for quick crew dropdowns and selectors."""
    id: int
    name: str
    rank_name: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CrewLedgerEntry(BaseModel):
    """Detailed historical ledger entry representing a voyage payout to a crew member."""
    id: int
    voyage_id: int
    voyage_name: str
    crew_member_id: int
    crew_member_name: str
    rank_name: str
    share_weight_units_used: int
    share_value_paise: int
    payout_paise: int
    status: str
    calculated_at: datetime
    finalized_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CrewBalanceResponse(BaseModel):
    """Running cumulative payout balance in integer paise for a crew member."""
    crew_member_id: int
    crew_member_name: str
    rank_name: Optional[str] = None
    running_balance_paise: int = Field(..., description="Cumulative dividend earnings from finalized payouts in integer paise")

    model_config = ConfigDict(from_attributes=True)

