"""
Pydantic schemas for Voyage validation and serialization.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class VoyageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Voyage or raid mission name")
    date: datetime = Field(..., description="Expedition departure or raid date")
    description: Optional[str] = Field(None, description="Optional mission context or target notes")
    revenue_paise: int = Field(default=0, strict=True, ge=0, description="Gross loot revenue in integer paise (₹1 = 100 paise)")
    status: str = Field(
        default="planned",
        pattern="^(planned|ongoing|in_progress|completed|cancelled)$",
        description="Voyage status (planned, ongoing, in_progress, completed, cancelled)"
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Voyage name cannot be empty or whitespace only")
        return trimmed


class VoyageCreate(VoyageBase):
    """Request payload for logging a new voyage."""
    pass


class VoyageUpdate(BaseModel):
    """Request payload for updating voyage loot revenue or operational status."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    date: Optional[datetime] = None
    description: Optional[str] = None
    revenue_paise: Optional[int] = Field(None, strict=True, ge=0)
    status: Optional[str] = Field(None, pattern="^(planned|ongoing|in_progress|completed|cancelled)$")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Voyage name cannot be empty or whitespace only")
            return trimmed
        return v


class VoyageResponse(VoyageBase):
    """Response model for a voyage with calculated metrics in integer units."""
    id: int
    total_expenses_paise: Optional[int] = Field(None, description="Total voyage expenses in integer paise")
    net_profit_paise: Optional[int] = Field(None, description="Gross revenue minus expenses in integer paise")
    profit_margin_basis_points: Optional[int] = Field(None, description="Profit margin in integer basis points (10000 = 100%, 2500 = 25%)")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VoyageSummary(BaseModel):
    """Lightweight summary model for voyage listings and table displays."""
    id: int
    name: str
    date: datetime
    revenue_paise: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class VoyageFinancialSummaryResponse(BaseModel):
    """Financial snapshot response for a voyage with zero-loss integer paise metrics."""
    voyage_id: int
    voyage_name: str
    revenue_paise: int = Field(..., description="Effective gross revenue in integer paise")
    expenses_paise: int = Field(..., description="Effective operational expenses in integer paise")
    net_profit_paise: int = Field(..., description="Net profit (revenue - expenses) in integer paise; can be negative (loss)")
    distributable_profit_paise: int = Field(..., description="Distributable profit in integer paise; 0 if net_profit <= 0")
    status: str

    model_config = ConfigDict(from_attributes=True)


class RevenuePostRequest(BaseModel):
    """Request payload for posting gross voyage revenue as an immutable CREDIT transaction."""
    revenue_paise: Optional[int] = Field(None, strict=True, gt=0, description="Optional gross revenue in integer paise")
    description: Optional[str] = Field(None, description="Audit note or revenue description")

