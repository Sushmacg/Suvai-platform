import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.modules.orders import service
from app.modules.orders.schemas import (
    OrderAdminResponse,
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
)
from app.modules.users.models import User

router = APIRouter(prefix="/orders", tags=["orders"])


# ---------- Customer ----------
@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    data: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_order(db, user, data)


# The "/me" routes are declared before "/{order_id}" so "me" is never read as an ID.
@router.get("/me", response_model=list[OrderResponse])
def my_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_orders(db, user, status_filter, limit, offset)


@router.get("/me/{order_id}", response_model=OrderResponse)
def my_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_my_order(db, user, order_id)


@router.post("/me/{order_id}/cancel", response_model=OrderResponse)
def cancel_my_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.cancel_my_order(db, user, order_id)


# ---------- Admin ----------
@router.get("", response_model=list[OrderAdminResponse])
def all_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    session_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.list_orders(db, status_filter, session_id, limit, offset)


@router.get("/{order_id}", response_model=OrderAdminResponse)
def one_order(
    order_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.get_order(db, order_id)


@router.patch("/{order_id}/status", response_model=OrderAdminResponse)
def change_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.change_status(db, order_id, data.status)
