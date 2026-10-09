import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate


def list_products(
    db: Session,
    include_inactive: bool = False,
    available_only: bool = False,
    category: str | None = None,
) -> list[Product]:
    query = select(Product).order_by(Product.name)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    if available_only:
        query = query.where(Product.is_available.is_(True))
    if category:
        query = query.where(Product.category == category.strip().lower())
    return list(db.scalars(query).all())


def get_product(db: Session, product_id: uuid.UUID, include_inactive: bool = False) -> Product:
    product = db.get(Product, product_id)
    if not product or (not include_inactive and not product.is_active):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


def _ensure_name_free(db: Session, name: str, ignore_id: uuid.UUID | None = None) -> None:
    existing = db.scalar(select(Product).where(Product.name == name))
    if existing and existing.id != ignore_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "A product with this name already exists")


def create_product(db: Session, data: ProductCreate) -> Product:
    _ensure_name_free(db, data.name)
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: uuid.UUID, data: ProductUpdate) -> Product:
    product = get_product(db, product_id, include_inactive=True)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        _ensure_name_free(db, changes["name"], ignore_id=product.id)
    for field, value in changes.items():
        if value is None and field in ("name", "category", "price"):
            continue  # required fields cannot be cleared
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def deactivate_product(db: Session, product_id: uuid.UUID) -> None:
    product = get_product(db, product_id, include_inactive=True)
    product.is_active = False
    db.commit()
