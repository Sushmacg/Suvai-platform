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
from fastapi import HTTPException, status
from app.modules.notifications import devices, dispatch
from app.modules.notifications.device_schemas import DeviceTokenRequest, DispatchSummary
from app.modules.notifications.fcm import PushSender, get_push_sender

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


@router.post("/device-token", status_code=status.HTTP_204_NO_CONTENT)
def register_device_token(
    data: DeviceTokenRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices.register_token(db, user, data.token, data.platform)


@router.delete("/device-token", status_code=status.HTTP_204_NO_CONTENT)
def remove_device_token(
    token: str = Query(..., min_length=20, max_length=512),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices.remove_token(db, user, token)


@router.post("/dispatch", response_model=DispatchSummary)
def dispatch_pending_notifications(
    _admin: User = Depends(require_role("admin")),
    sender: PushSender | None = Depends(get_push_sender),
    db: Session = Depends(get_db),
):
    if sender is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Push delivery is not configured"
        )
    return dispatch.dispatch_pending(db, sender)