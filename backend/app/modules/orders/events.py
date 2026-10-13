import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import ClassVar

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderLine:
    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True, kw_only=True)
class OrderCreated(DomainEvent):
    event_type: ClassVar[str] = "order.created"

    order_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    session_id: uuid.UUID
    location_id: uuid.UUID
    location_name: str
    session_date: date
    total_amount: Decimal
    items: tuple[OrderLine, ...]

    @property
    def aggregate_id(self) -> uuid.UUID:
        return self.order_id


@dataclass(frozen=True, kw_only=True)
class OrderCancelled(DomainEvent):
    event_type: ClassVar[str] = "order.cancelled"

    order_id: uuid.UUID
    customer_id: uuid.UUID
    session_id: uuid.UUID
    cancelled_by: str  # "customer" or "admin"
    total_amount: Decimal
    items: tuple[OrderLine, ...]

    @property
    def aggregate_id(self) -> uuid.UUID:
        return self.order_id
