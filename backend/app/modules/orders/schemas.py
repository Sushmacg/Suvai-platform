import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.stalls.schemas import SessionResponse

OrderStatus = Literal[
    "pending", "confirmed", "preparing", "ready", "completed", "cancelled"
]


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    session_id: uuid.UUID
    items: list[OrderItemCreate] = Field(min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=300)


class OrderStatusUpdate(BaseModel):
    status: Literal["confirmed", "preparing", "ready", "completed", "cancelled"]


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    total_amount: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]
    session: SessionResponse  # where and when to pick the order up


class OrderAdminResponse(OrderResponse):
    customer_id: uuid.UUID
    customer_name: str
    customer_phone: str
