"""
Pydantic schemas for Immutable Append-Only Transaction Log serialization.
Notice: To uphold strict financial audit immutability, NO TransactionUpdate or TransactionDelete schemas exist.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TransactionResponse(BaseModel):
    """
    Public response model for an immutable treasury transaction log entry.
    All financial amounts are stored as positive integer paise; transaction_type defines direction.
    """
    id: int
    voyage_id: Optional[int] = Field(None, description="Associated Voyage ID if tied to an expedition")
    transaction_type: str = Field(
        ...,
        pattern="^(CREDIT|DEBIT|REVERSAL|CORRECTION)$",
        description="Transaction classification (CREDIT, DEBIT, REVERSAL, CORRECTION)"
    )
    amount_paise: int = Field(..., strict=True, gt=0, description="Positive transaction amount in integer paise")
    description: str = Field(..., description="Audit rationale or narrative explanation")
    timestamp: datetime = Field(..., description="Timestamp when the financial event occurred")
    reference_type: Optional[str] = Field(None, description="Originating entity type (e.g. voyage_revenue, expense, payout)")
    reference_id: Optional[int] = Field(None, description="Originating entity primary key")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionCreateInternal(BaseModel):
    """
    Internal schema used strictly by backend domain services to record immutable ledger entries.
    Never exposed directly to client input endpoints without domain validation.
    """
    voyage_id: Optional[int] = None
    transaction_type: str = Field(..., pattern="^(CREDIT|DEBIT|REVERSAL|CORRECTION)$")
    amount_paise: int = Field(..., strict=True, gt=0)
    description: str = Field(..., min_length=1, max_length=255)
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None


class TransactionReversalRequest(BaseModel):
    """Request payload for reversing an existing transaction in the immutable ledger."""
    reason: str = Field(..., min_length=1, max_length=255, description="Audit reason for the transaction reversal")


class TransactionCorrectionRequest(BaseModel):
    """Request payload for correcting an immutable transaction."""
    new_amount_paise: int = Field(..., strict=True, gt=0, description="Corrected amount in integer paise")
    reason: str = Field(..., min_length=1, max_length=255, description="Audit reason for the correction")

