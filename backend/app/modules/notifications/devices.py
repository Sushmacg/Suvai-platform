from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.notifications.models import DeviceToken
from app.modules.users.models import User


def register_token(db: Session, user: User, token: str, platform: str) -> None:
    """Save a device token. A token seen on a new account moves to that account."""
    row = db.scalar(select(DeviceToken).where(DeviceToken.token == token))
    if row is None:
        db.add(DeviceToken(user_id=user.id, token=token, platform=platform))
    else:
        row.user_id = user.id
        row.platform = platform
    db.commit()


def remove_token(db: Session, user: User, token: str) -> None:
    """Remove the caller's own token. Other users' tokens are never touched."""
    db.execute(
        delete(DeviceToken).where(
            DeviceToken.token == token, DeviceToken.user_id == user.id
        )
    )
    db.commit()