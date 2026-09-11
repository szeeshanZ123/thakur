"""
API Router for Voyage Operational Expenses.
"""

from typing import List, Optional
from datetime import datetime
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.core.database import get_db
from backend.models.expense import Expense
from backend.models.voyage import Voyage
from backend.models.transaction import TransactionLog
from backend.models.user import User
from backend.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from backend.schemas.analytics import PaginatedResponse
from backend.dependencies.auth import require_crew_or_above, require_captain

router = APIRouter(prefix="/api/expenses", tags=["Expenses"])


@router.get("", response_model=PaginatedResponse[ExpenseResponse], summary="List operational expenses with filters")
def list_expenses(
    voyage_id: Optional[int] = Query(None, description="Filter by voyage ID"),
    category: Optional[str] = Query(None, description="Filter by expense category"),
    date_from: Optional[datetime] = Query(None, description="Filter incurred on or after"),
    date_to: Optional[datetime] = Query(None, description="Filter incurred on or before"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crew_or_above)
):
    """Retrieve paginated operational expenses with optional voyage, category, and date range filters."""
    query = db.query(Expense)

    if voyage_id is not None:
        query = query.filter(Expense.voyage_id == voyage_id)
    if category:
        query = query.filter(Expense.category.ilike(f"%{category.strip()}%"))
    if date_from:
        query = query.filter(Expense.date >= date_from)
    if date_to:
        query = query.filter(Expense.date <= date_to)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    expenses = query.order_by(Expense.date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse[ExpenseResponse](
        items=expenses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED, summary="Record a new operational expense")
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    captain_user: User = Depends(require_captain)
):
    """Record an operational expense against an expedition in integer paise."""
    # Verify voyage exists
    voyage = db.query(Voyage).filter(Voyage.id == payload.voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {payload.voyage_id} not found."
        )

    expense = Expense(
        voyage_id=payload.voyage_id,
        category=payload.category,
        amount_paise=payload.amount_paise,
        date=payload.date,
        description=payload.description
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    return expense


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Get expense by ID")
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crew_or_above)
):
    """Retrieve details for a single operational expense entry."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found."
        )
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse, summary="Update an unposted operational expense")
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    captain_user: User = Depends(require_captain)
):
    """
    Update an unposted expense entry.
    If the expense has already been posted to the immutable TransactionLog, editing is rejected (409 Conflict).
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found."
        )

    # Check if posted to immutable transaction log
    is_posted = db.query(TransactionLog).filter(
        TransactionLog.reference_type == "expense",
        TransactionLog.reference_id == expense_id
    ).first()

    if is_posted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Posted financial expenses cannot be edited. Create a reversal/correction instead."
        )

    if payload.category is not None:
        expense.category = payload.category
    if payload.amount_paise is not None:
        expense.amount_paise = payload.amount_paise
    if payload.date is not None:
        expense.date = payload.date
    if payload.description is not None:
        expense.description = payload.description

    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_200_OK, summary="Delete an unposted operational expense")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    captain_user: User = Depends(require_captain)
):
    """
    Delete an unposted expense.
    If the expense has been posted to TransactionLog, deletion is rejected (409 Conflict).
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found."
        )

    is_posted = db.query(TransactionLog).filter(
        TransactionLog.reference_type == "expense",
        TransactionLog.reference_id == expense_id
    ).first()

    if is_posted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Posted expenses cannot be deleted. Create a reversal instead."
        )

    db.delete(expense)
    db.commit()
    return {"message": f"Expense {expense_id} successfully deleted.", "id": expense_id}
