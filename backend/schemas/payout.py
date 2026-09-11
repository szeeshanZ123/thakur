"""
Pydantic schemas for Voyage Dividend Payout Calculations and Finalization.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PayoutResponse(BaseModel):
    """Response model for a finalized or calculated individual pirate payout."""
    id: int
    voyage_id: int
    crew_member_id: int
    crew_member_name: Optional[str] = None
    rank_name: Optional[str] = None
    share_weight_units_used: int = Field(..., description="Historical share weight snapshot used during calculation")
    share_value_paise: int = Field(..., description="Calculated value per share unit in integer paise")
    payout_paise: int = Field(..., description="Total dividend payout allocated to the pirate in integer paise")
    status: str = Field(..., description="Payout status (calculated, approved, paid)")
    calculated_at: datetime
    finalized_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayoutPreviewItem(BaseModel):
    """Itemized distribution row for a crew member in a payout preview calculation."""
    crew_member_id: int
    crew_member_name: str
    rank_name: str
    share_weight_units: int
    payout_paise: int


class PayoutPreview(BaseModel):
    """
    Transparent calculation breakdown returned for client review before dividend finalization.
    Guarantees zero-loss integer reconciliation:
    distributable_profit_paise = SUM(items.payout_paise) + remainder_paise.
    """
    voyage_id: int
    voyage_name: str
    revenue_paise: int = Field(..., description="Gross voyage revenue in integer paise")
    total_expenses_paise: int = Field(..., description="Sum of all voyage operational expenses in integer paise")
    net_profit_paise: int = Field(..., description="Gross revenue minus operational expenses in integer paise")
    total_share_units: int = Field(..., description="Sum of all active participating crew share weight units")
    share_value_paise: int = Field(..., description="Floor integer division value per share unit")
    distributable_profit_paise: int = Field(..., description="Total net profit allocated for division")
    remainder_paise: int = Field(default=0, description="Fractional remainder allocated to ship's maintenance chest")
    items: List[PayoutPreviewItem] = Field(default_factory=list, description="Per-pirate distribution allocations")


class PayoutFinalizeResponse(BaseModel):
    """Response returned upon committing and finalizing an immutable dividend distribution."""
    voyage_id: int
    status: str = Field(default="finalized")
    total_distributed_paise: int
    payouts: List[PayoutResponse] = Field(default_factory=list)
