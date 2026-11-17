import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.modules.products.media import media_root
from app.modules.products.models import Product, ProductImage
from app.modules.products.service import get_product

MAX_IMAGES = 10
MAX_BYTES = 5 * 1024 * 1024
URL_PREFIX = "/media/products/"


def _detect(head: bytes) -> str | None:
    """File type from the real bytes, never from the client's file name or content type."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _sync_cover(product: Product) -> None:
    if product.images:
        product.image_url = product.images[0].url
    elif product.image_url and product.image_url.startswith(URL_PREFIX):
        product.image_url = None


def _file_for(url: str) -> Path:
    return media_root() / "products" / Path(url).name


def _get_image(product: Product, image_id: uuid.UUID) -> ProductImage:
    image = next((i for i in product.images if i.id == image_id), None)
    if image is None:
        raise HTTPException(404, "Image not found")
    return image


async def add_images(db: Session, product_id: uuid.UUID, files: list[UploadFile]) -> Product:
    product = get_product(db, product_id, include_inactive=True)
    if not files:
        raise HTTPException(422, "Choose at least one image")
    if len(product.images) + len(files) > MAX_IMAGES:
        raise HTTPException(422, f"A product can have at most {MAX_IMAGES} images")
    saved: list[Path] = []
    try:
        position = max((i.position for i in product.images), default=-1) + 1
        for upload in files:
            data = await upload.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise HTTPException(413, "Each image must be 5 MB or smaller")
            ext = _detect(data[:12])
            if ext is None:
                raise HTTPException(415, "Only JPG, PNG or WebP images are allowed")
            name = f"{uuid.uuid4().hex}.{ext}"
            path = media_root() / "products" / name
            path.write_bytes(data)
            saved.append(path)
            db.add(ProductImage(product_id=product.id, url=f"{URL_PREFIX}{name}", position=position))
            position += 1
        db.flush()
        db.refresh(product, ["images"])
        _sync_cover(product)
        db.commit()
    except Exception:
        db.rollback()
        for path in saved:
            path.unlink(missing_ok=True)
        raise
    db.refresh(product)
    return product


def set_cover(db: Session, product_id: uuid.UUID, image_id: uuid.UUID) -> Product:
    product = get_product(db, product_id, include_inactive=True)
    cover = _get_image(product, image_id)
    for index, image in enumerate([cover] + [i for i in product.images if i.id != cover.id]):
        image.position = index
    db.flush()
    db.refresh(product, ["images"])
    _sync_cover(product)
    db.commit()
    db.refresh(product)
    return product


def remove_image(db: Session, product_id: uuid.UUID, image_id: uuid.UUID) -> Product:
    product = get_product(db, product_id, include_inactive=True)
    image = _get_image(product, image_id)
    path = _file_for(image.url)
    db.delete(image)
    db.flush()
    db.refresh(product, ["images"])
    _sync_cover(product)
    db.commit()
    path.unlink(missing_ok=True)
    db.refresh(product)
    return product