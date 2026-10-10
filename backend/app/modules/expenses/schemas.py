import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ExpenseCategory = Literal[
    "ingredients",
    "packaging",
    "fuel",
    "transport",
    "rent",
    "labour",
    "utilities",
    "marketing",
    "maintenance",
    "other",
]


def _clean_description(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category: ExpenseCategory
    description: str | None = Field(default=None, max_length=500)
    expense_date: date | None = None  # defaults to today (India) in the service
    session_id: uuid.UUID | None = None

    _clean = field_validator("description")(_clean_description)


class ExpenseUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category: ExpenseCategory | None = None
    description: str | None = Field(default=None, max_length=500)
    expense_date: date | None = None
    session_id: uuid.UUID | None = None

    _clean = field_validator("description")(_clean_description)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    category: str
    description: str | None
    expense_date: date
    session_id: uuid.UUID | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ExpenseSummary(BaseModel):
    total: Decimal
    count: int
    by_category: dict[str, Decimal]
