from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.modules.notifications import service
from app.modules.notifications.schemas import (
    Audience,
    NotificationAdminResponse,
    NotificationResponse,
    NotificationStatus,
)
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/me", response_model=list[NotificationResponse])
def my_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_for_user(db, user, limit, offset)


@router.get("", response_model=list[NotificationAdminResponse])
def all_notifications(
    status_filter: NotificationStatus | None = Query(None, alias="status"),
    audience: Audience | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.list_all(db, status_filter, audience, limit, offset)
