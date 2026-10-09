import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_category(value: str | None) -> str | None:
    return value.strip().lower() if value else value


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    category: str = Field(default="nankhatai", min_length=2, max_length=50)
    price: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool = True

    _normalize = field_validator("category")(_clean_category)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    category: str | None = Field(default=None, min_length=2, max_length=50)
    price: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool | None = None
    is_active: bool | None = None

    _normalize = field_validator("category")(_clean_category)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    category: str
    price: Decimal
    image_url: str | None
    is_available: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
