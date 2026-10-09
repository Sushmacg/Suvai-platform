import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.products.models import Product


class SessionStock(Base):
    """How much of one product is on the stall for one session."""

    __tablename__ = "session_stock"
    __table_args__ = (
        UniqueConstraint("session_id", "product_id", name="uq_session_stock_session_product"),
        CheckConstraint("stocked_qty >= 0", name="ck_session_stock_stocked_nonneg"),
        CheckConstraint("sold_qty >= 0", name="ck_session_stock_sold_nonneg"),
        CheckConstraint("wasted_qty >= 0", name="ck_session_stock_wasted_nonneg"),
        CheckConstraint("min_stock >= 0", name="ck_session_stock_min_nonneg"),
        # Remaining stock can never go below zero, enforced by PostgreSQL itself.
        CheckConstraint(
            "sold_qty + wasted_qty <= stocked_qty", name="ck_session_stock_never_negative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stall_sessions.id", ondelete="CASCADE")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), index=True
    )
    stocked_qty: Mapped[int] = mapped_column(Integer, default=0)
    sold_qty: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    wasted_qty: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    min_stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped[Product] = relationship()

    # ---- computed values (never stored, so they cannot drift) ----
    @property
    def available_qty(self) -> int:
        return self.stocked_qty - self.sold_qty - self.wasted_qty

    @property
    def is_low_stock(self) -> bool:
        return self.min_stock > 0 and self.available_qty <= self.min_stock

    @property
    def in_stock(self) -> bool:
        return self.available_qty > 0 and self.product.is_available

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def price(self) -> Decimal:
        return self.product.price
