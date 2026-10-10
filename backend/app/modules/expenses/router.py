import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.expenses import service
from app.modules.expenses.schemas import (
    ExpenseCategory,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSummary,
    ExpenseUpdate,
)
from app.modules.users.models import User

# Every route in this module is admin-only, enforced once at the router level.
router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
    dependencies=[Depends(require_role("admin"))],
)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: ExpenseCreate,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.create_expense(db, admin, data)


# "/summary" is declared before "/{expense_id}" so it is never read as an ID.
@router.get("/summary", response_model=ExpenseSummary)
def summary(
    category: ExpenseCategory | None = None,
    start: date | None = None,
    end: date | None = None,
    session_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    return service.summarize(db, category, start, end, session_id)


@router.get("", response_model=list[ExpenseResponse])
def list_all(
    category: ExpenseCategory | None = None,
    start: date | None = None,
    end: date | None = None,
    session_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.list_expenses(db, category, start, end, session_id, limit, offset)


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_one(expense_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.get_expense(db, expense_id)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update(expense_id: uuid.UUID, data: ExpenseUpdate, db: Session = Depends(get_db)):
    return service.update_expense(db, expense_id, data)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(expense_id: uuid.UUID, db: Session = Depends(get_db)):
    service.delete_expense(db, expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
