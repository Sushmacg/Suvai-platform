import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.products.service import get_product
from app.modules.reviews.models import Review
from app.modules.reviews.schemas import RatingSummary, ReviewCreate, ReviewUpdate
from app.modules.users.models import User

DUPLICATE = "You have already reviewed this product. Edit your review instead."


def _query():
    return select(Review).options(
        selectinload(Review.customer), selectinload(Review.product)
    )


def _load(db: Session, review_id: uuid.UUID) -> Review:
    review = db.scalar(
        _query().where(Review.id == review_id).execution_options(populate_existing=True)
    )
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    return review


def _has_bought(db: Session, customer_id: uuid.UUID, product_id: uuid.UUID) -> bool:
    """True only if the customer has a COMPLETED order containing this product."""
    return (
        db.scalar(
            select(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.customer_id == customer_id,
                Order.status == "completed",
                OrderItem.product_id == product_id,
            )
            .limit(1)
        )
        is not None
    )


# ---------------- customer ----------------
def create_review(db: Session, user: User, data: ReviewCreate) -> Review:
    get_product(db, data.product_id)  # 404 if the product is missing or removed
    if not _has_bought(db, user.id, data.product_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can review a product after you have received it in a completed order",
        )
    if db.scalar(
        select(Review.id).where(
            Review.customer_id == user.id, Review.product_id == data.product_id
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)

    review = Review(
        customer_id=user.id,
        product_id=data.product_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:  # two requests raced; the unique constraint caught it
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)
    return _load(db, review.id)


def _own_review(db: Session, user: User, review_id: uuid.UUID) -> Review:
    review = _load(db, review_id)
    if review.customer_id != user.id:
        # Same answer as "missing", so other people's review IDs are not revealed.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    return review


def list_my_reviews(db: Session, user: User, limit: int, offset: int) -> list[Review]:
    query = (
        _query()
        .where(Review.customer_id == user.id)
        .order_by(Review.created_at.desc(), Review.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all())


def get_my_review(db: Session, user: User, review_id: uuid.UUID) -> Review:
    return _own_review(db, user, review_id)


def update_my_review(
    db: Session, user: User, review_id: uuid.UUID, data: ReviewUpdate
) -> Review:
    review = _own_review(db, user, review_id)
    changes = data.model_dump(exclude_unset=True)
    if "rating" in changes and changes["rating"] is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rating cannot be empty")
    if not changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to update")
    for field, value in changes.items():
        setattr(review, field, value)
    db.commit()
    return _load(db, review_id)


def delete_my_review(db: Session, user: User, review_id: uuid.UUID) -> None:
    review = _own_review(db, user, review_id)
    db.delete(review)
    db.commit()


# ---------------- public ----------------
def list_product_reviews(
    db: Session, product_id: uuid.UUID, limit: int, offset: int
) -> list[Review]:
    get_product(db, product_id)
    query = (
        _query()
        .where(Review.product_id == product_id, Review.is_hidden.is_(False))
        .order_by(Review.created_at.desc(), Review.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all())


def rating_summary(db: Session, product_id: uuid.UUID) -> RatingSummary:
    get_product(db, product_id)
    rows = db.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.product_id == product_id, Review.is_hidden.is_(False))
        .group_by(Review.rating)
    ).all()
    stars = {str(n): 0 for n in range(1, 6)}
    for rating, count in rows:
        stars[str(rating)] = count
    total = sum(stars.values())
    average = (
        round(sum(int(star) * count for star, count in stars.items()) / total, 2)
        if total
        else None
    )
    return RatingSummary(product_id=product_id, average=average, count=total, stars=stars)


# ---------------- admin moderation ----------------
def list_all_reviews(
    db: Session,
    product_id: uuid.UUID | None,
    hidden: bool | None,
    rating: int | None,
    limit: int,
    offset: int,
) -> list[Review]:
    query = _query()
    if product_id:
        query = query.where(Review.product_id == product_id)
    if hidden is not None:
        query = query.where(Review.is_hidden.is_(hidden))
    if rating:
        query = query.where(Review.rating == rating)
    query = query.order_by(Review.created_at.desc(), Review.id).limit(limit).offset(offset)
    return list(db.scalars(query).all())


def get_review(db: Session, review_id: uuid.UUID) -> Review:
    return _load(db, review_id)


def hide_review(db: Session, review_id: uuid.UUID, reason: str | None) -> Review:
    review = _load(db, review_id)
    review.is_hidden = True
    review.hidden_reason = reason.strip() if reason and reason.strip() else None
    db.commit()
    return _load(db, review_id)


def restore_review(db: Session, review_id: uuid.UUID) -> Review:
    review = _load(db, review_id)
    review.is_hidden = False
    review.hidden_reason = None
    db.commit()
    return _load(db, review_id)


def delete_review(db: Session, review_id: uuid.UUID) -> None:
    review = _load(db, review_id)
    db.delete(review)
    db.commit()
