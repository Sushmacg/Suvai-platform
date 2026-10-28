import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    """A message waiting to be delivered. A future Firebase worker will drain 'pending' rows."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "audience IN ('user', 'admins', 'all_customers')", name="ck_notifications_audience"
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed')", name="ck_notifications_status"
        ),
        # A 'user' notification must name the user; the others must not.
        CheckConstraint(
            "(audience = 'user') = (user_id IS NOT NULL)", name="ck_notifications_user_audience"
        ),
        Index("ix_notifications_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50))
    audience: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(
        String(10), default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceToken(Base):
    """A phone registered for push messages. One row per FCM token."""

    __tablename__ = "device_tokens"
    __table_args__ = (
        CheckConstraint("platform IN ('android', 'ios')", name="ck_device_tokens_platform"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(512), unique=True)
    platform: Mapped[str] = mapped_column(
        String(10), default="android", server_default="android"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )