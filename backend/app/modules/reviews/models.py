import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.products.models import Product
from app.modules.users.models import User


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
        # One review per customer per product, enforced by PostgreSQL itself.
        UniqueConstraint("customer_id", "product_id", name="uq_reviews_customer_product"),
        Index("ix_reviews_product_visible", "product_id", "is_hidden"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Moderation: hidden reviews stay in the table but are not shown publicly.
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    hidden_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[User] = relationship()
    product: Mapped[Product] = relationship()

    @property
    def reviewer_name(self) -> str:
        """First name only, so public pages never expose full names."""
        parts = self.customer.name.split()
        return parts[0] if parts else "Customer"

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def customer_name(self) -> str:
        return self.customer.name

    @property
    def customer_phone(self) -> str:
        return self.customer.phone
