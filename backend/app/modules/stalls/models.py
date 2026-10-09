import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StallLocation(Base):
    """A saved spot where the stall sets up, e.g. 'Market Gate'."""

    __tablename__ = "stall_locations"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_stall_locations_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_stall_locations_longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    google_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StallSession(Base):
    """One day's stall visit to one location (scheduled -> open -> closed)."""

    __tablename__ = "stall_sessions"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_stall_sessions_time_order"),
        CheckConstraint(
            "status IN ('scheduled', 'open', 'closed', 'cancelled')",
            name="ck_stall_sessions_status",
        ),
        UniqueConstraint(
            "location_id", "session_date", "start_time", name="uq_stall_sessions_slot"
        ),
        Index("ix_stall_sessions_date_status", "session_date", "status"),
        # At most ONE row may have status 'open', enforced by PostgreSQL itself.
        Index(
            "uq_stall_sessions_one_open",
            "status",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stall_locations.id"), index=True
    )
    session_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    location: Mapped[StallLocation] = relationship()
