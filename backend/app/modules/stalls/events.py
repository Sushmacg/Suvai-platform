import uuid
from dataclasses import dataclass
from datetime import date, time
from typing import ClassVar

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class StallScheduleUpdated(DomainEvent):
    """change is one of: created, updated, opened, closed, cancelled, deleted."""

    event_type: ClassVar[str] = "stall.schedule_updated"

    session_id: uuid.UUID
    change: str
    location_id: uuid.UUID
    location_name: str
    session_date: date
    start_time: time
    end_time: time
    status: str

    @property
    def aggregate_id(self) -> uuid.UUID:
        return self.session_id
