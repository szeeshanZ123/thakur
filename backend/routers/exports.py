"""
API Router for Exportable Voyage Financial Manifests.
Provides verified JSON and CSV manifest downloads for auditing and spreadsheet analysis.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.export import VoyageManifestResponse
from backend.services.export_service import (
    build_voyage_manifest,
    export_voyage_json,
    export_voyage_csv,
    get_safe_export_filename,
)

router = APIRouter(prefix="/api/voyages", tags=["Voyage Exports & Manifests"])


def _verify_export_role(role: Optional[str] = None) -> str:
    """Validate user role for export access."""
    active_role = (role or "captain").lower().strip()
    if active_role not in ["admin", "captain", "crew"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized to export voyage financial manifests."
        )
    return active_role


@router.get(
    "/{voyage_id}/export/json",
    summary="Export Voyage Financial Manifest as JSON",
    description="Generate and download a comprehensive, verifiable JSON financial manifest for the specified voyage."
)
def export_manifest_json(
    voyage_id: int,
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_export_role(x_user_role)
    json_str = export_voyage_json(db=db, voyage_id=voyage_id)
    filename = get_safe_export_filename(voyage_id, "json")

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get(
    "/{voyage_id}/export/csv",
    summary="Export Voyage Financial Manifest as CSV",
    description="Generate and download a spreadsheet-compatible CSV financial manifest (Excel / Google Sheets / LibreOffice) with formula injection protection."
)
def export_manifest_csv(
    voyage_id: int,
    x_user_role: Optional[str] = Header("captain", alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    _verify_export_role(x_user_role)
    csv_str = export_voyage_csv(db=db, voyage_id=voyage_id)
    filename = get_safe_export_filename(voyage_id, "csv")

    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
