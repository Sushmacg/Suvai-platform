import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.event_log.models import EventLog


def list_events(
    db: Session,
    event_type: str | None,
    aggregate_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> list[EventLog]:
    query = select(EventLog)
    if event_type:
        query = query.where(EventLog.event_type == event_type)
    if aggregate_id:
        query = query.where(EventLog.aggregate_id == aggregate_id)
    query = query.order_by(EventLog.occurred_at.desc(), EventLog.id).limit(limit).offset(offset)
    return list(db.scalars(query).all())
