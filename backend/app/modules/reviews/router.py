import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.modules.reviews import service
from app.modules.reviews.schemas import (
    AdminReviewResponse,
    HideRequest,
    MyReviewResponse,
    PublicReviewResponse,
    RatingSummary,
    ReviewCreate,
    ReviewUpdate,
)
from app.modules.users.models import User

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ---------- Customer ----------
@router.post("", response_model=MyReviewResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_review(db, user, data)


# Fixed paths ("/me", "/product", "/admin") are declared before "/{review_id}" routes.
@router.get("/me", response_model=list[MyReviewResponse])
def my_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_my_reviews(db, user, limit, offset)


@router.get("/me/{review_id}", response_model=MyReviewResponse)
def my_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_my_review(db, user, review_id)


@router.patch("/me/{review_id}", response_model=MyReviewResponse)
def update_my_review(
    review_id: uuid.UUID,
    data: ReviewUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.update_my_review(db, user, review_id, data)


@router.delete("/me/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.delete_my_review(db, user, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Public ----------
@router.get("/product/{product_id}", response_model=list[PublicReviewResponse])
def product_reviews(
    product_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.list_product_reviews(db, product_id, limit, offset)


@router.get("/product/{product_id}/summary", response_model=RatingSummary)
def product_summary(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.rating_summary(db, product_id)


# ---------- Admin moderation ----------
@router.get("/admin", response_model=list[AdminReviewResponse])
def admin_list(
    product_id: uuid.UUID | None = None,
    hidden: bool | None = None,
    rating: int | None = Query(None, ge=1, le=5),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.list_all_reviews(db, product_id, hidden, rating, limit, offset)


@router.get("/admin/{review_id}", response_model=AdminReviewResponse)
def admin_get(
    review_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.get_review(db, review_id)


@router.post("/admin/{review_id}/hide", response_model=AdminReviewResponse)
def admin_hide(
    review_id: uuid.UUID,
    data: HideRequest,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.hide_review(db, review_id, data.reason)


@router.post("/admin/{review_id}/restore", response_model=AdminReviewResponse)
def admin_restore(
    review_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.restore_review(db, review_id)


@router.delete("/admin/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete(
    review_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service.delete_review(db, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
