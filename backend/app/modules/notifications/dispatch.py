"""Drain 'pending' notifications and deliver them to registered devices."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.notifications.fcm import PushSender
from app.modules.notifications.models import DeviceToken, Notification
from app.modules.users.models import User

logger = logging.getLogger(__name__)

MAX_BATCH = 200


def _tokens_for(db: Session, notification: Notification) -> list[DeviceToken]:
    query = (
        select(DeviceToken)
        .join(User, User.id == DeviceToken.user_id)
        .where(User.is_active.is_(True))
    )
    if notification.audience == "user":
        query = query.where(DeviceToken.user_id == notification.user_id)
    elif notification.audience == "admins":
        query = query.where(User.role == "admin")
    else:  # all_customers
        query = query.where(User.role == "customer")
    return list(db.scalars(query).all())


def dispatch_pending(db: Session, sender: PushSender, limit: int = MAX_BATCH) -> dict:
    pending = db.scalars(
        select(Notification)
        .where(Notification.status == "pending")
        .order_by(Notification.created_at, Notification.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    summary = {
        "considered": 0,
        "sent": 0,
        "failed": 0,
        "no_devices": 0,
        "invalid_tokens_removed": 0,
    }
    for notification in pending:
        summary["considered"] += 1
        tokens = _tokens_for(db, notification)
        if not tokens:
            notification.status = "failed"
            summary["failed"] += 1
            summary["no_devices"] += 1
            db.commit()
            continue
        delivered = False
        for device in tokens:
            result = sender.send(
                device.token,
                notification.title,
                notification.body,
                {"event_type": notification.event_type},
            )
            if result.ok:
                delivered = True
            elif result.invalid_token:
                db.delete(device)
                summary["invalid_tokens_removed"] += 1
            else:
                logger.warning(
                    "FCM send failed for notification %s: %s", notification.id, result.error
                )
        if delivered:
            notification.status = "sent"
            notification.sent_at = datetime.now(timezone.utc)
            summary["sent"] += 1
        else:
            notification.status = "failed"
            summary["failed"] += 1
        db.commit()
    return summary