"""
Financial Business Service for Captain's Treasure Ledger.
Handles zero-loss integer calculations, immutable transaction ledger posting,
atomic expense debits, revenue credits, reversals, and corrections.
"""

from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.models.voyage import Voyage
from backend.models.expense import Expense
from backend.models.transaction import TransactionLog


def calculate_voyage_effective_revenue(db: Session, voyage_id: int) -> int:
    """
    Calculate net effective revenue for a voyage in integer paise:
    Total Credits - Reversals of Credits.
    Falls back to Voyage.revenue_paise if no CREDIT transaction entries exist.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    all_txs = db.query(TransactionLog).filter(TransactionLog.voyage_id == voyage_id).all()
    credit_txs = [t for t in all_txs if t.transaction_type == "CREDIT"]
    if not credit_txs:
        return voyage.revenue_paise

    credits = sum(t.amount_paise for t in credit_txs)

    # Subtract reversals that target a CREDIT transaction
    reversals_on_credits = 0
    tx_by_id = {t.id: t for t in all_txs}
    for t in all_txs:
        if t.transaction_type == "REVERSAL" and t.reference_id and t.reference_id in tx_by_id:
            referenced_tx = tx_by_id[t.reference_id]
            if referenced_tx.transaction_type == "CREDIT":
                reversals_on_credits += t.amount_paise

    return credits - reversals_on_credits


def calculate_voyage_effective_expenses(db: Session, voyage_id: int) -> int:
    """
    Calculate net effective operational expenses for a voyage in integer paise:
    Total Debits - Reversals of Debits.
    Falls back to sum(Expense.amount_paise) if no DEBIT transaction entries exist.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    all_txs = db.query(TransactionLog).filter(TransactionLog.voyage_id == voyage_id).all()
    debit_txs = [t for t in all_txs if t.transaction_type == "DEBIT"]
    if not debit_txs:
        return sum(e.amount_paise for e in voyage.expenses) if voyage.expenses else 0

    debits = sum(t.amount_paise for t in debit_txs)

    # Subtract reversals that target a DEBIT transaction
    reversals_on_debits = 0
    tx_by_id = {t.id: t for t in all_txs}
    for t in all_txs:
        if t.transaction_type == "REVERSAL" and t.reference_id and t.reference_id in tx_by_id:
            referenced_tx = tx_by_id[t.reference_id]
            if referenced_tx.transaction_type == "DEBIT":
                reversals_on_debits += t.amount_paise

    return debits - reversals_on_debits



def calculate_net_profit(db: Session, voyage_id: int) -> int:
    """
    Calculate exact net profit in integer paise:
    Net Revenue - Net Expenses.
    Can be positive, zero, or negative (loss).
    """
    revenue = calculate_voyage_effective_revenue(db, voyage_id)
    expenses = calculate_voyage_effective_expenses(db, voyage_id)
    return revenue - expenses


def calculate_distributable_profit(db: Session, voyage_id: int) -> int:
    """
    Calculate distributable net profit in integer paise:
    Clamped to 0 if net profit <= 0 (losses are absorbed by the ship, not distributed as negative dividend).
    """
    net_profit = calculate_net_profit(db, voyage_id)
    return max(0, net_profit)


def get_voyage_financial_summary(db: Session, voyage_id: int) -> Dict[str, Any]:
    """
    Retrieve comprehensive financial snapshot for a voyage in integer paise.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    revenue = calculate_voyage_effective_revenue(db, voyage_id)
    expenses = calculate_voyage_effective_expenses(db, voyage_id)
    net_profit = revenue - expenses
    distributable_profit = max(0, net_profit)

    return {
        "voyage_id": voyage.id,
        "voyage_name": voyage.name,
        "revenue_paise": revenue,
        "expenses_paise": expenses,
        "net_profit_paise": net_profit,
        "distributable_profit_paise": distributable_profit,
        "status": voyage.status
    }


def post_revenue_transaction(
    db: Session,
    voyage_id: int,
    revenue_paise: Optional[int] = None,
    description: Optional[str] = None
) -> TransactionLog:
    """
    Atomically post a CREDIT transaction for a voyage's gross loot revenue.
    Enforces idempotency: rejects duplicate active revenue postings for the same voyage.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    if voyage.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot post revenue for a cancelled voyage."
        )

    # Check for existing unreversed revenue posting (idempotency guard)
    existing_credit = db.query(TransactionLog).filter(
        TransactionLog.voyage_id == voyage_id,
        TransactionLog.transaction_type == "CREDIT",
        TransactionLog.reference_type == "voyage_revenue",
        TransactionLog.reference_id == voyage_id
    ).first()

    if existing_credit:
        # Check if it was already reversed
        is_reversed = db.query(TransactionLog).filter(
            TransactionLog.transaction_type == "REVERSAL",
            TransactionLog.reference_type == "transaction",
            TransactionLog.reference_id == existing_credit.id
        ).first()

        if not is_reversed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Revenue for voyage '{voyage.name}' (ID: {voyage_id}) has already been posted in transaction #{existing_credit.id}."
            )

    amount = revenue_paise if revenue_paise is not None else voyage.revenue_paise
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Revenue amount must be greater than zero to post a credit transaction."
        )

    # Update voyage revenue if new amount provided
    if revenue_paise is not None:
        voyage.revenue_paise = revenue_paise

    desc = description or f"Gross loot revenue from expedition: {voyage.name}"

    tx = TransactionLog(
        voyage_id=voyage_id,
        transaction_type="CREDIT",
        amount_paise=amount,
        description=desc,
        reference_type="voyage_revenue",
        reference_id=voyage_id,
        timestamp=datetime.utcnow()
    )

    try:
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to post revenue transaction atomically: {str(e)}"
        )


def create_and_post_expense(
    db: Session,
    voyage_id: int,
    category: str,
    amount_paise: int,
    date: datetime,
    description: Optional[str] = None
) -> Tuple[Expense, TransactionLog]:
    """
    Atomically create an Expense and post a corresponding DEBIT transaction to the immutable ledger.
    If either fails, the entire database transaction is rolled back.
    """
    voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
    if not voyage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voyage with ID {voyage_id} not found."
        )

    if voyage.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record operational expenses for a cancelled voyage."
        )

    if amount_paise <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense amount must be greater than zero."
        )

    try:
        # 1. Create Expense record
        expense = Expense(
            voyage_id=voyage_id,
            category=category,
            amount_paise=amount_paise,
            date=date,
            description=description
        )
        db.add(expense)
        db.flush()  # Populates expense.id

        # 2. Create immutable DEBIT TransactionLog entry
        desc = description or f"Operational cost: {category} for voyage '{voyage.name}'"
        tx = TransactionLog(
            voyage_id=voyage_id,
            transaction_type="DEBIT",
            amount_paise=amount_paise,
            description=desc,
            reference_type="expense",
            reference_id=expense.id,
            timestamp=datetime.utcnow()
        )
        db.add(tx)

        # 3. Commit both atomically
        db.commit()
        db.refresh(expense)
        db.refresh(tx)
        return expense, tx
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Atomic expense and debit transaction creation failed: {str(e)}"
        )


def post_reversal_transaction(
    db: Session,
    transaction_id: int,
    reason: str
) -> TransactionLog:
    """
    Atomically create a REVERSAL transaction for an existing financial transaction.
    The original transaction is NEVER modified or deleted.
    Prevents duplicate reversals of the same transaction.
    """
    original_tx = db.query(TransactionLog).filter(TransactionLog.id == transaction_id).first()
    if not original_tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found."
        )

    if original_tx.transaction_type == "REVERSAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reverse an existing reversal transaction."
        )

    # Check if already reversed
    existing_reversal = db.query(TransactionLog).filter(
        TransactionLog.transaction_type == "REVERSAL",
        TransactionLog.reference_type == "transaction",
        TransactionLog.reference_id == transaction_id
    ).first()

    if existing_reversal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transaction #{transaction_id} has already been reversed by Transaction #{existing_reversal.id}."
        )

    reversal_tx = TransactionLog(
        voyage_id=original_tx.voyage_id,
        transaction_type="REVERSAL",
        amount_paise=original_tx.amount_paise,
        description=f"Reversal of Tx #{transaction_id} ({original_tx.transaction_type} {original_tx.amount_paise} paise): {reason}",
        reference_type="transaction",
        reference_id=transaction_id,
        timestamp=datetime.utcnow()
    )

    try:
        db.add(reversal_tx)
        db.commit()
        db.refresh(reversal_tx)
        return reversal_tx
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record reversal transaction: {str(e)}"
        )


def post_correction_transaction(
    db: Session,
    original_transaction_id: int,
    new_amount_paise: int,
    reason: str
) -> Tuple[TransactionLog, TransactionLog]:
    """
    Atomically post a correction:
    1. Reverses original transaction.
    2. Creates a new transaction with corrected amount_paise.
    Full historical audit trail is preserved.
    """
    original_tx = db.query(TransactionLog).filter(TransactionLog.id == original_transaction_id).first()
    if not original_tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {original_transaction_id} not found."
        )

    if new_amount_paise <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrected amount must be greater than zero."
        )

    try:
        # 1. Reverse original transaction
        reversal_tx = TransactionLog(
            voyage_id=original_tx.voyage_id,
            transaction_type="REVERSAL",
            amount_paise=original_tx.amount_paise,
            description=f"Correction Reversal of Tx #{original_transaction_id}: {reason}",
            reference_type="transaction",
            reference_id=original_transaction_id,
            timestamp=datetime.utcnow()
        )
        db.add(reversal_tx)
        db.flush()

        # 2. Create corrected replacement transaction
        corrected_tx = TransactionLog(
            voyage_id=original_tx.voyage_id,
            transaction_type=original_tx.transaction_type,  # Keep same direction (CREDIT or DEBIT)
            amount_paise=new_amount_paise,
            description=f"Corrected replacement for Tx #{original_transaction_id}: {reason}",
            reference_type="transaction_correction",
            reference_id=original_transaction_id,
            timestamp=datetime.utcnow()
        )
        db.add(corrected_tx)

        db.commit()
        db.refresh(reversal_tx)
        db.refresh(corrected_tx)
        return reversal_tx, corrected_tx
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to post correction transactions: {str(e)}"
        )
