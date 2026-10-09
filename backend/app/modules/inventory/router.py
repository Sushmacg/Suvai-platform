import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.inventory import service
from app.modules.inventory.schemas import (
    StockAdminResponse,
    StockPublicResponse,
    StockSet,
    WasteCreate,
)
from app.modules.users.models import User

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ---------- Customer (public, read-only) ----------
@router.get("/sessions/{session_id}", response_model=list[StockPublicResponse])
def availability(session_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.list_stock(db, session_id, public=True)


# ---------- Admin ----------
@router.get("/sessions/{session_id}/admin", response_model=list[StockAdminResponse])
def admin_stock(
    session_id: uuid.UUID,
    low_stock_only: bool = Query(False),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.list_stock(db, session_id, low_stock_only=low_stock_only)


@router.put(
    "/sessions/{session_id}/products/{product_id}", response_model=StockAdminResponse
)
def set_stock(
    session_id: uuid.UUID,
    product_id: uuid.UUID,
    data: StockSet,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.set_stock(db, session_id, product_id, data)


@router.post(
    "/sessions/{session_id}/products/{product_id}/waste",
    response_model=StockAdminResponse,
)
def record_waste(
    session_id: uuid.UUID,
    product_id: uuid.UUID,
    data: WasteCreate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.record_waste(db, session_id, product_id, data.quantity)
