"""
Pydantic schemas for Exportable Voyage Financial Manifests (JSON and CSV).
Enforces integer paise for monetary metrics and captures historical payout snapshots.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class VoyageManifestMetadata(BaseModel):
    """Metadata detailing the manifest version and export timestamp."""
    manifest_version: str = Field("1.0", description="Manifest format version schema")
    exported_at: datetime = Field(..., description="Timestamp of when the export was generated")
    export_format: str = Field(..., description="'json' or 'csv'")
    voyage_id: int = Field(..., description="Unique voyage identifier")


class VoyageManifestInfo(BaseModel):
    """Core expedition details."""
    id: int
    name: str
    date: datetime
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class VoyageManifestFinancialSummary(BaseModel):
    """Reconciled financial snapshot from the Phase 5 engine."""
    revenue_paise: int = Field(..., description="Effective gross revenue in integer paise")
    expenses_paise: int = Field(..., description="Effective operational expenses in integer paise")
    net_profit_paise: int = Field(..., description="Net profit (revenue - expenses) in integer paise")
    distributable_profit_paise: int = Field(..., description="Distributable profit (clamped to 0 for losses)")


class VoyageManifestCrewItem(BaseModel):
    """Crew member participating in the expedition."""
    crew_member_id: int
    name: str
    rank: str
    current_share_weight_units: int
    is_active: bool


class VoyageManifestExpenseItem(BaseModel):
    """Itemized operational expense record."""
    expense_id: int
    category: str
    amount_paise: int
    date: datetime
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class VoyageManifestPayoutItem(BaseModel):
    """Historical finalized dividend payout record."""
    payout_id: int
    crew_member_id: int
    crew_member_name: str
    rank: str
    share_weight_units_used: int = Field(..., description="Historical snapshot of share weight at payout finalization")
    payout_paise: int = Field(..., description="Allocated dividend amount in integer paise")
    status: str
    calculated_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None


class VoyageManifestTransactionItem(BaseModel):
    """Immutable audit trail transaction log record."""
    transaction_id: int
    transaction_type: str = Field(..., description="'CREDIT', 'DEBIT', 'REVERSAL', or 'CORRECTION'")
    amount_paise: int
    description: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    timestamp: datetime
    created_at: Optional[datetime] = None


class VoyageManifestResponse(BaseModel):
    """Comprehensive JSON Voyage Manifest structure."""
    manifest_version: str = "1.0"
    exported_at: datetime
    export_format: str = "json"
    voyage: VoyageManifestInfo
    financial_summary: VoyageManifestFinancialSummary
    payout_status: str = Field("NOT_FINALIZED", description="'FINALIZED' or 'NOT_FINALIZED'")
    crew: List[VoyageManifestCrewItem] = Field(default_factory=list)
    expenses: List[VoyageManifestExpenseItem] = Field(default_factory=list)
    payouts: List[VoyageManifestPayoutItem] = Field(default_factory=list)
    transactions: List[VoyageManifestTransactionItem] = Field(default_factory=list)
