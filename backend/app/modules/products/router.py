import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.products import service
from app.modules.products.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.modules.users.models import User

router = APIRouter(prefix="/products", tags=["products"])


# ---------- Customer (public) ----------
@router.get("", response_model=list[ProductResponse])
def list_menu(db: Session = Depends(get_db)):
    return service.list_products(db)


# ---------- Admin ----------
# Declared before "/{product_id}" so "admin/all" is not read as an ID.
@router.get("/admin/all", response_model=list[ProductResponse])
def admin_list_all(
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.list_products(db, include_inactive=True)


@router.get("/{product_id}", response_model=ProductResponse)
def get_one(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.get_product(db, product_id)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: ProductCreate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.create_product(db, data)


@router.patch("/{product_id}", response_model=ProductResponse)
def update(
    product_id: uuid.UUID,
    data: ProductUpdate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.update_product(db, product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate(
    product_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service.deactivate_product(db, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
