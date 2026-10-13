from sqlalchemy.orm import Session

from app.core.events import DomainEvent
from app.modules.event_log.models import EventLog


def record_event(db: Session, event: DomainEvent) -> None:
    """Subscribed to every event. Writes in the same transaction as the business change."""
    db.add(
        EventLog(
            id=event.event_id,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            payload=event.payload(),
            occurred_at=event.occurred_at,
        )
    )
