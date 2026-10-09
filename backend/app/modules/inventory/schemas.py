import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StockSet(BaseModel):
    stocked_qty: int = Field(ge=0, le=100000)
    min_stock: int | None = Field(default=None, ge=0, le=100000)


class WasteCreate(BaseModel):
    quantity: int = Field(gt=0, le=100000)


class StockAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    stocked_qty: int
    sold_qty: int
    wasted_qty: int
    available_qty: int
    min_stock: int
    is_low_stock: bool
    updated_at: datetime


class StockPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    product_name: str
    price: Decimal
    available_qty: int
    in_stock: bool
