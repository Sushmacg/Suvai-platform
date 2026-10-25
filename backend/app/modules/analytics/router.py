from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.analytics import service

# Every route is admin-only and read-only.
router = APIRouter(
    prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_role("admin"))]
)
Days = Annotated[int, Query(ge=1, le=365)]


@router.get("/summary")
def summary(days: Days = 30, db: Session = Depends(get_db)):
    return service.summary(db, days)


@router.get("/sales")
def sales(days: Days = 30, db: Session = Depends(get_db)):
    return service.sales(db, days)


@router.get("/products")
def products(days: Days = 30, limit: Annotated[int, Query(ge=1, le=50)] = 10, db: Session = Depends(get_db)):
    return service.products(db, days, limit)


@router.get("/locations")
def locations(days: Days = 30, db: Session = Depends(get_db)):
    return service.locations(db, days)