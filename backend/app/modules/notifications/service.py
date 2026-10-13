import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent
from app.modules.notifications.models import Notification
from app.modules.users.models import User


def queue_notification(
    db: Session,
    *,
    event: DomainEvent,
    audience: str,
    title: str,
    body: str,
    user_id: uuid.UUID | None = None,
) -> Notification:
    """Queue a message as 'pending'. Delivery (Firebase) comes later."""
    notification = Notification(
        event_id=event.event_id,
        event_type=event.event_type,
        audience=audience,
        user_id=user_id,
        title=title[:120],
        body=body[:300],
    )
    db.add(notification)
    return notification


def list_for_user(db: Session, user: User, limit: int, offset: int) -> list[Notification]:
    audiences = ["all_customers"] if user.role == "customer" else ["admins"]
    query = (
        select(Notification)
        .where(or_(Notification.user_id == user.id, Notification.audience.in_(audiences)))
        .order_by(Notification.created_at.desc(), Notification.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all())


def list_all(
    db: Session,
    status_filter: str | None,
    audience: str | None,
    limit: int,
    offset: int,
) -> list[Notification]:
    query = select(Notification)
    if status_filter:
        query = query.where(Notification.status == status_filter)
    if audience:
        query = query.where(Notification.audience == audience)
    query = query.order_by(Notification.created_at.desc(), Notification.id).limit(limit).offset(offset)
    return list(db.scalars(query).all())
