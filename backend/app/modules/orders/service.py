import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.inventory.service import release_stock, reserve_stock
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schemas import OrderCreate
from app.modules.products.models import Product
from app.modules.stalls.models import StallSession
from app.modules.stalls.service import get_session, today_ist
from app.modules.users.models import User

ORDERABLE_SESSION_STATUSES = ("scheduled", "open")
MAX_QTY_PER_PRODUCT = 50

# current status -> statuses it may move to
ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"completed", "cancelled"},
}


# ---------------- loading ----------------
def _order_query():
    return select(Order).options(
        selectinload(Order.items),
        selectinload(Order.customer),
        selectinload(Order.session).selectinload(StallSession.location),
    )


def _load_order(
    db: Session,
    order_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
    lock: bool = False,
) -> Order:
    query = (
        _order_query()
        .where(Order.id == order_id)
        .execution_options(populate_existing=True)
    )
    if customer_id is not None:
        query = query.where(Order.customer_id == customer_id)
    if lock:
        # Hold a row lock until we commit, so two requests cannot change one order at once.
        query = query.with_for_update(of=Order)
    order = db.scalar(query)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


# ---------------- placing an order ----------------
def create_order(db: Session, user: User, data: OrderCreate) -> Order:
    # 1. Merge duplicate products and check quantities.
    wanted: dict[uuid.UUID, int] = {}
    for item in data.items:
        wanted[item.product_id] = wanted.get(item.product_id, 0) + item.quantity
    if any(qty > MAX_QTY_PER_PRODUCT for qty in wanted.values()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"You can order at most {MAX_QTY_PER_PRODUCT} of one product",
        )

    # 2. The session must exist and still be orderable.
    session = get_session(db, data.session_id)
    if session.status not in ORDERABLE_SESSION_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"This stall session is {session.status}"
        )
    if session.session_date < today_ist():
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This stall session has already passed"
        )

    # 3. Every product must exist and be on sale.
    products = {
        p.id: p
        for p in db.scalars(select(Product).where(Product.id.in_(list(wanted))))
    }
    for product_id in wanted:
        product = products.get(product_id)
        if product is None or not product.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {product_id} not found")
        if not product.is_available:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"{product.name} is not available right now"
            )

    # 4. Build the order with the prices as they are right now.
    order = Order(
        customer_id=user.id,
        session_id=session.id,
        status="pending",
        notes=data.notes,
        total_amount=Decimal("0.00"),
    )
    total = Decimal("0.00")
    for product_id, quantity in wanted.items():
        product = products[product_id]
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price,
            )
        )
        total += product.price * quantity
    order.total_amount = total.quantize(Decimal("0.01"))

    # 5. One transaction: save the order AND take the stock, or neither.
    session_id = session.id
    try:
        db.add(order)
        db.flush()
        order_id = order.id
        reserve_stock(db, session_id, list(wanted.items()))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _load_order(db, order_id)


# ---------------- customer views ----------------
def list_my_orders(
    db: Session,
    user: User,
    status_filter: str | None,
    limit: int,
    offset: int,
) -> list[Order]:
    query = _order_query().where(Order.customer_id == user.id)
    if status_filter:
        query = query.where(Order.status == status_filter)
    query = query.order_by(Order.created_at.desc(), Order.id).limit(limit).offset(offset)
    return list(db.scalars(query).all())


def get_my_order(db: Session, user: User, order_id: uuid.UUID) -> Order:
    return _load_order(db, order_id, customer_id=user.id)


def cancel_my_order(db: Session, user: User, order_id: uuid.UUID) -> Order:
    order = _load_order(db, order_id, customer_id=user.id, lock=True)
    if order.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only pending orders can be cancelled here. Please contact the stall.",
        )
    return _apply_status(db, order, "cancelled")


# ---------------- admin views ----------------
def list_orders(
    db: Session,
    status_filter: str | None,
    session_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> list[Order]:
    query = _order_query()
    if status_filter:
        query = query.where(Order.status == status_filter)
    if session_id:
        query = query.where(Order.session_id == session_id)
    query = query.order_by(Order.created_at.desc(), Order.id).limit(limit).offset(offset)
    return list(db.scalars(query).all())


def get_order(db: Session, order_id: uuid.UUID) -> Order:
    return _load_order(db, order_id)


def change_status(db: Session, order_id: uuid.UUID, new_status: str) -> Order:
    order = _load_order(db, order_id, lock=True)
    return _apply_status(db, order, new_status)


# ---------------- status changes ----------------
def _apply_status(db: Session, order: Order, new_status: str) -> Order:
    if new_status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change a '{order.status}' order to '{new_status}'",
        )
    order_id = order.id
    try:
        if new_status == "cancelled":
            # Stock goes back in the same transaction as the status change.
            release_stock(
                db,
                order.session_id,
                [(item.product_id, item.quantity) for item in order.items],
            )
        order.status = new_status
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _load_order(db, order_id)
