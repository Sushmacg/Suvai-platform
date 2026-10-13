from sqlalchemy.orm import Session

from app.modules.inventory.service import release_stock, reserve_stock
from app.modules.orders.events import OrderCancelled, OrderCreated


def reserve_stock_for_order(db: Session, event: OrderCreated) -> None:
    """Raises HTTP 409 if anything is short. The order transaction then rolls back."""
    reserve_stock(
        db, event.session_id, [(line.product_id, line.quantity) for line in event.items]
    )


def release_stock_for_order(db: Session, event: OrderCancelled) -> None:
    release_stock(
        db, event.session_id, [(line.product_id, line.quantity) for line in event.items]
    )
