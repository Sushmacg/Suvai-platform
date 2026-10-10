import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.expenses.models import Expense
from app.modules.expenses.schemas import ExpenseCreate, ExpenseSummary, ExpenseUpdate
from app.modules.stalls.models import StallSession
from app.modules.stalls.service import today_ist
from app.modules.users.models import User

REQUIRED_FIELDS = ("amount", "category", "expense_date")


def _check_date(value: date) -> None:
    if value > today_ist():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Expense date cannot be in the future")


def _check_session(db: Session, session_id: uuid.UUID | None) -> None:
    if session_id is not None and db.get(StallSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stall session not found")


def _filtered(
    query,
    category: str | None,
    start: date | None,
    end: date | None,
    session_id: uuid.UUID | None,
):
    if category:
        query = query.where(Expense.category == category)
    if start:
        query = query.where(Expense.expense_date >= start)
    if end:
        query = query.where(Expense.expense_date <= end)
    if session_id:
        query = query.where(Expense.session_id == session_id)
    return query


def _check_range(start: date | None, end: date | None) -> None:
    if start and end and start > end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start must not be after end")


def create_expense(db: Session, admin: User, data: ExpenseCreate) -> Expense:
    expense_date = data.expense_date or today_ist()
    _check_date(expense_date)
    _check_session(db, data.session_id)

    expense = Expense(
        amount=data.amount,
        category=data.category,
        description=data.description,
        expense_date=expense_date,
        session_id=data.session_id,
        created_by=admin.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def get_expense(db: Session, expense_id: uuid.UUID) -> Expense:
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    return expense


def list_expenses(
    db: Session,
    category: str | None,
    start: date | None,
    end: date | None,
    session_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> list[Expense]:
    _check_range(start, end)
    query = _filtered(select(Expense), category, start, end, session_id)
    query = (
        query.order_by(Expense.expense_date.desc(), Expense.created_at.desc(), Expense.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all())


def update_expense(db: Session, expense_id: uuid.UUID, data: ExpenseUpdate) -> Expense:
    expense = get_expense(db, expense_id)
    changes = data.model_dump(exclude_unset=True)

    for field in REQUIRED_FIELDS:
        if field in changes and changes[field] is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field} cannot be empty")
    if "expense_date" in changes:
        _check_date(changes["expense_date"])
    if "session_id" in changes:
        _check_session(db, changes["session_id"])  # sending null unlinks the session

    for field, value in changes.items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, expense_id: uuid.UUID) -> None:
    expense = get_expense(db, expense_id)
    db.delete(expense)
    db.commit()


def summarize(
    db: Session,
    category: str | None,
    start: date | None,
    end: date | None,
    session_id: uuid.UUID | None,
) -> ExpenseSummary:
    """Totals only. Analytics will build profit reports on top of this later."""
    _check_range(start, end)
    query = _filtered(
        select(Expense.category, func.sum(Expense.amount), func.count(Expense.id)),
        category,
        start,
        end,
        session_id,
    ).group_by(Expense.category)

    by_category: dict[str, Decimal] = {}
    total = Decimal("0.00")
    count = 0
    for name, amount, rows in db.execute(query):
        by_category[name] = amount
        total += amount
        count += rows
    return ExpenseSummary(total=total, count=count, by_category=by_category)
