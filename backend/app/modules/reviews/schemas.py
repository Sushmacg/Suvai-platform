import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_comment(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ReviewCreate(BaseModel):
    product_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

    _clean = field_validator("comment")(_clean_comment)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

    _clean = field_validator("comment")(_clean_comment)


class HideRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class PublicReviewResponse(BaseModel):
    """What anyone browsing a product sees."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reviewer_name: str
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime


class MyReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    rating: int
    comment: str | None
    is_hidden: bool
    created_at: datetime
    updated_at: datetime


class AdminReviewResponse(MyReviewResponse):
    customer_id: uuid.UUID
    customer_name: str
    customer_phone: str
    hidden_reason: str | None


class RatingSummary(BaseModel):
    product_id: uuid.UUID
    average: float | None
    count: int
    stars: dict[str, int]  # "1" .. "5" -> how many reviews
