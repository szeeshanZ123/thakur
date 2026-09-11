"""
Pydantic schemas for Operational Expense validation and serialization.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ExpenseBase(BaseModel):
    voyage_id: int = Field(..., strict=True, gt=0, description="Associated Voyage ID")
    category: str = Field(..., min_length=1, max_length=50, description="Expense category (e.g. Ship Repair, Gunpowder, Provisions)")
    amount_paise: int = Field(..., strict=True, gt=0, description="Expense cost in integer paise (₹1 = 100 paise)")
    date: datetime = Field(default_factory=datetime.utcnow, description="Date the expense was incurred")
    description: Optional[str] = Field(None, max_length=255, description="Itemized receipt description or invoice notes")

    @field_validator("category")
    @classmethod
    def validate_category_not_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Expense category cannot be empty or whitespace only")
        return trimmed


class ExpenseCreate(ExpenseBase):
    """Request payload for logging an operational voyage expense."""
    pass


class ExpenseUpdate(BaseModel):
    """
    Request payload for updating unfinalized expense entries.
    Note: Once a financial transaction is committed to TransactionLog, modifications require reversal.
    """
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount_paise: Optional[int] = Field(None, strict=True, gt=0)
    date: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("category")
    @classmethod
    def validate_category_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Expense category cannot be empty or whitespace only")
            return trimmed
        return v


class ExpenseResponse(ExpenseBase):
    """Response model for a recorded operational expense."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
