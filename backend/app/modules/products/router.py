import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.products import images as image_service
from app.modules.products import service
from app.modules.products.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.modules.users.models import User

router = APIRouter(prefix="/products", tags=["products"])


# ---------- Customer (public) ----------
@router.get("", response_model=list[ProductResponse])
def list_menu(
    available_only: bool = Query(False, description="Hide sold-out products"),
    category: str | None = Query(None, max_length=50),
    db: Session = Depends(get_db),
):
    return service.list_products(db, available_only=available_only, category=category)


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


# ---------- Admin: product photos ----------
@router.post(
    "/{product_id}/images",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_images(
    product_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return await image_service.add_images(db, product_id, files)


@router.put("/{product_id}/images/{image_id}/cover", response_model=ProductResponse)
def make_cover(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return image_service.set_cover(db, product_id, image_id)


@router.delete("/{product_id}/images/{image_id}", response_model=ProductResponse)
def delete_image(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return image_service.remove_image(db, product_id, image_id)