import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EXPENSE_CATEGORIES = (
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
)
_CATEGORY_SQL = ", ".join(f"'{c}'" for c in EXPENSE_CATEGORIES)


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        CheckConstraint(f"category IN ({_CATEGORY_SQL})", name="ck_expenses_category"),
        Index("ix_expenses_date_category", "expense_date", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date] = mapped_column(Date)
    # Optional link, so analytics can compute profit per stall session.
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stall_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
