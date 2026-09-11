"""
Export Service for Captain's Treasure Ledger.
Generates comprehensive, immutable financial voyage manifests in JSON and CSV formats.

CRITICAL EXPORT INVARIANTS:
- All monetary amounts remain exact INTEGER PAISE.
- Historical payouts preserve share_weight_units_used from the snapshot at finalization time.
- All transaction logs (CREDIT, DEBIT, REVERSAL, CORRECTION) are fully included for complete auditability.
- Purely read-only: exports never create or mutate database state.
- CSV exports include formula injection defense for spreadsheet security (Excel/Sheets/LibreOffice).
"""

import io
import csv
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog
from backend.models.crew import CrewMember
from backend.models.payout import Payout
from backend.services.financial_service import get_voyage_financial_summary


def _sanitize_csv_cell(val: Any) -> str:
    """
    Sanitizes values against CSV Formula Injection.
    If a string starts with =, +, -, or @, it is escaped with a leading single quote.
    """
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@"):
        return f"'{s}"
    return s


def get_safe_export_filename(voyage_id: int, format_ext: str = "json") -> str:
    """
    Generates a sanitized, path-traversal-safe filename for downloads.
    """
    ext = format_ext.lower().strip(".")
    if ext not in ["json", "csv"]:
        ext = "json"
    return f"voyage_{voyage_id}_manifest.{ext}"


def build_voyage_manifest(db: Session, voyage_id: int) -> Dict[str, Any]:
    """
    Extracts and compiles complete financial and operational data for a single voyage.
    Read-only operation with zero database side effects.
    """
    voyage = (
        db.query(Voyage)
        .options(
            joinedload(Voyage.expenses),
            joinedload(Voyage.transaction_logs),
            joinedload(Voyage.payouts).joinedload(Payout.crew_member)
        )
        .filter(Voyage.id == voyage_id)
        .first()
    )

    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    # 1. Financial summary from Phase 5 engine
    fin_summary = get_voyage_financial_summary(db=db, voyage_id=voyage_id)

    # 2. Active crew roster
    active_crew = db.query(CrewMember).options(joinedload(CrewMember.rank)).filter(CrewMember.is_active == True).all()
    crew_list = []
    for c in active_crew:
        crew_list.append({
            "crew_member_id": c.id,
            "name": c.name,
            "rank": c.rank.name if c.rank else "Unassigned",
            "current_share_weight_units": c.rank.share_weight_units if c.rank else 0,
            "is_active": c.is_active,
        })

    # 3. Itemized expenses
    expenses = db.query(Expense).filter(Expense.voyage_id == voyage_id).order_by(Expense.date.asc(), Expense.id.asc()).all()
    expense_list = []
    for e in expenses:
        expense_list.append({
            "expense_id": e.id,
            "category": e.category,
            "amount_paise": e.amount_paise,
            "date": e.date.isoformat() if e.date else None,
            "description": e.description,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    # 4. Finalized payouts (Historical snapshot preserved)
    payouts = (
        db.query(Payout)
        .options(joinedload(Payout.crew_member).joinedload(CrewMember.rank))
        .filter(Payout.voyage_id == voyage_id)
        .order_by(Payout.id.asc())
        .all()
    )

    payout_status = "FINALIZED" if payouts else "NOT_FINALIZED"
    payout_list = []
    for p in payouts:
        rank_title = p.crew_member.rank.name if (p.crew_member and p.crew_member.rank) else "Unknown"
        payout_list.append({
            "payout_id": p.id,
            "crew_member_id": p.crew_member_id,
            "crew_member_name": p.crew_member.name if p.crew_member else "Unknown",
            "rank": rank_title,
            "share_weight_units_used": p.share_weight_units_used,
            "payout_paise": p.payout_paise,
            "status": p.status,
            "calculated_at": p.calculated_at.isoformat() if p.calculated_at else None,
            "finalized_at": p.finalized_at.isoformat() if p.finalized_at else None,
        })

    # 5. Full chronological immutable transaction ledger
    transactions = (
        db.query(TransactionLog)
        .filter(TransactionLog.voyage_id == voyage_id)
        .order_by(TransactionLog.timestamp.asc(), TransactionLog.id.asc())
        .all()
    )
    transaction_list = []
    for t in transactions:
        transaction_list.append({
            "transaction_id": t.id,
            "transaction_type": t.transaction_type,
            "amount_paise": t.amount_paise,
            "description": t.description,
            "reference_type": t.reference_type,
            "reference_id": t.reference_id,
            "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    now = datetime.now(UTC)

    return {
        "manifest_version": "1.0",
        "exported_at": now.isoformat(),
        "export_format": "json",
        "voyage": {
            "id": voyage.id,
            "name": voyage.name,
            "date": voyage.date.isoformat() if voyage.date else None,
            "description": voyage.description,
            "status": voyage.status,
            "created_at": voyage.created_at.isoformat() if voyage.created_at else None,
        },
        "financial_summary": {
            "revenue_paise": fin_summary["revenue_paise"],
            "expenses_paise": fin_summary["expenses_paise"],
            "net_profit_paise": fin_summary["net_profit_paise"],
            "distributable_profit_paise": fin_summary["distributable_profit_paise"],
        },
        "payout_status": payout_status,
        "crew": crew_list,
        "expenses": expense_list,
        "payouts": payout_list,
        "transactions": transaction_list,
    }


def export_voyage_json(db: Session, voyage_id: int) -> str:
    """
    Serialize the complete voyage manifest into formatted JSON.
    """
    manifest = build_voyage_manifest(db, voyage_id)
    manifest["export_format"] = "json"
    return json.dumps(manifest, indent=2)


def export_voyage_csv(db: Session, voyage_id: int) -> str:
    """
    Serialize the voyage manifest into a clean, spreadsheet-compatible CSV
    with structured record_type discriminators and formula injection defense.
    """
    manifest = build_voyage_manifest(db, voyage_id)

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # CSV Header
    headers = [
        "record_type",
        "id",
        "voyage_id",
        "name",
        "category_or_rank",
        "amount_paise",
        "share_weight_units",
        "date_or_timestamp",
        "description_or_status",
        "reference_type",
        "reference_id"
    ]
    writer.writerow(headers)

    # 1. Voyage Info Row
    v = manifest["voyage"]
    writer.writerow([
        "voyage",
        _sanitize_csv_cell(v["id"]),
        _sanitize_csv_cell(v["id"]),
        _sanitize_csv_cell(v["name"]),
        "",
        "",
        "",
        _sanitize_csv_cell(v["date"]),
        _sanitize_csv_cell(v["status"]),
        "",
        ""
    ])

    # 2. Financial Summary Rows
    fs = manifest["financial_summary"]
    writer.writerow([
        "financial_summary",
        "",
        _sanitize_csv_cell(v["id"]),
        "Gross Revenue",
        "REVENUE",
        _sanitize_csv_cell(fs["revenue_paise"]),
        "",
        _sanitize_csv_cell(manifest["exported_at"]),
        _sanitize_csv_cell(manifest["payout_status"]),
        "",
        ""
    ])
    writer.writerow([
        "financial_summary",
        "",
        _sanitize_csv_cell(v["id"]),
        "Operational Expenses",
        "EXPENSES",
        _sanitize_csv_cell(fs["expenses_paise"]),
        "",
        _sanitize_csv_cell(manifest["exported_at"]),
        _sanitize_csv_cell(manifest["payout_status"]),
        "",
        ""
    ])
    writer.writerow([
        "financial_summary",
        "",
        _sanitize_csv_cell(v["id"]),
        "Net Profit",
        "NET_PROFIT",
        _sanitize_csv_cell(fs["net_profit_paise"]),
        "",
        _sanitize_csv_cell(manifest["exported_at"]),
        _sanitize_csv_cell(manifest["payout_status"]),
        "",
        ""
    ])
    writer.writerow([
        "financial_summary",
        "",
        _sanitize_csv_cell(v["id"]),
        "Distributable Profit",
        "DISTRIBUTABLE_PROFIT",
        _sanitize_csv_cell(fs["distributable_profit_paise"]),
        "",
        _sanitize_csv_cell(manifest["exported_at"]),
        _sanitize_csv_cell(manifest["payout_status"]),
        "",
        ""
    ])

    # 3. Active Crew Rows
    for c in manifest["crew"]:
        writer.writerow([
            "crew",
            _sanitize_csv_cell(c["crew_member_id"]),
            _sanitize_csv_cell(v["id"]),
            _sanitize_csv_cell(c["name"]),
            _sanitize_csv_cell(c["rank"]),
            "",
            _sanitize_csv_cell(c["current_share_weight_units"]),
            "",
            "ACTIVE" if c["is_active"] else "INACTIVE",
            "",
            ""
        ])

    # 4. Expense Rows
    for e in manifest["expenses"]:
        writer.writerow([
            "expense",
            _sanitize_csv_cell(e["expense_id"]),
            _sanitize_csv_cell(v["id"]),
            "",
            _sanitize_csv_cell(e["category"]),
            _sanitize_csv_cell(e["amount_paise"]),
            "",
            _sanitize_csv_cell(e["date"]),
            _sanitize_csv_cell(e["description"]),
            "",
            ""
        ])

    # 5. Finalized Payout Rows
    for p in manifest["payouts"]:
        writer.writerow([
            "payout",
            _sanitize_csv_cell(p["payout_id"]),
            _sanitize_csv_cell(v["id"]),
            _sanitize_csv_cell(p["crew_member_name"]),
            _sanitize_csv_cell(p["rank"]),
            _sanitize_csv_cell(p["payout_paise"]),
            _sanitize_csv_cell(p["share_weight_units_used"]),
            _sanitize_csv_cell(p["finalized_at"]),
            _sanitize_csv_cell(p["status"]),
            "",
            ""
        ])

    # 6. Transaction Ledger Rows
    for t in manifest["transactions"]:
        writer.writerow([
            "transaction",
            _sanitize_csv_cell(t["transaction_id"]),
            _sanitize_csv_cell(v["id"]),
            _sanitize_csv_cell(t["transaction_type"]),
            "",
            _sanitize_csv_cell(t["amount_paise"]),
            "",
            _sanitize_csv_cell(t["timestamp"]),
            _sanitize_csv_cell(t["description"]),
            _sanitize_csv_cell(t["reference_type"]),
            _sanitize_csv_cell(t["reference_id"])
        ])

    return output.getvalue()
