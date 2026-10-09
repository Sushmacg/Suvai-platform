import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.inventory.models import SessionStock
from app.modules.inventory.schemas import StockSet
from app.modules.products.service import get_product
from app.modules.stalls.service import get_session

EDITABLE_STATUSES = ("scheduled", "open")  # stock can be set / orders reserved
AVAILABLE = SessionStock.stocked_qty - SessionStock.sold_qty - SessionStock.wasted_qty


# ---------------- helpers ----------------
def _row_query(session_id: uuid.UUID, product_id: uuid.UUID):
    return (
        select(SessionStock)
        .options(selectinload(SessionStock.product))
        .where(SessionStock.session_id == session_id, SessionStock.product_id == product_id)
    )


def _load(db: Session, session_id: uuid.UUID, product_id: uuid.UUID) -> SessionStock:
    return db.scalars(_row_query(session_id, product_id)).one()


def _merge(items: list[tuple[uuid.UUID, int]]) -> dict[uuid.UUID, int]:
    """Combine duplicate products and validate quantities."""
    wanted: dict[uuid.UUID, int] = {}
    for product_id, quantity in items:
        if quantity <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantity must be positive")
        wanted[product_id] = wanted.get(product_id, 0) + quantity
    return wanted


def _shortage(db: Session, session_id: uuid.UUID, product_id: uuid.UUID) -> HTTPException:
    row = db.scalar(_row_query(session_id, product_id))
    if row is None:
        return HTTPException(
            status.HTTP_409_CONFLICT, "This product is not stocked for this session"
        )
    return HTTPException(
        status.HTTP_409_CONFLICT,
        f"Only {row.available_qty} left of {row.product.name}",
    )


# ---------------- reading ----------------
def list_stock(
    db: Session,
    session_id: uuid.UUID,
    public: bool = False,
    low_stock_only: bool = False,
) -> list[SessionStock]:
    get_session(db, session_id)  # 404 if the session does not exist
    rows = db.scalars(
        select(SessionStock)
        .options(selectinload(SessionStock.product))
        .where(SessionStock.session_id == session_id)
    ).all()
    if public:
        rows = [r for r in rows if r.product.is_active]
    if low_stock_only:
        rows = [r for r in rows if r.is_low_stock]
    return sorted(rows, key=lambda r: r.product.name)


# ---------------- admin writes ----------------
def set_stock(
    db: Session, session_id: uuid.UUID, product_id: uuid.UUID, data: StockSet
) -> SessionStock:
    session = get_session(db, session_id)
    if session.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Cannot change stock of a {session.status} session"
        )
    get_product(db, product_id)  # 404 if missing or inactive

    # Lock the row so a simultaneous order waits until this change is finished.
    row = db.scalar(_row_query(session_id, product_id).with_for_update(of=SessionStock))
    if row is None:
        db.add(
            SessionStock(
                session_id=session_id,
                product_id=product_id,
                stocked_qty=data.stocked_qty,
                min_stock=data.min_stock or 0,
            )
        )
    else:
        floor = row.sold_qty + row.wasted_qty
        if data.stocked_qty < floor:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Stock cannot be below {floor} (already sold or wasted)",
            )
        row.stocked_qty = data.stocked_qty
        if data.min_stock is not None:
            row.min_stock = data.min_stock
    try:
        db.commit()
    except IntegrityError:  # two admins created the same row at the same moment
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Stock was changed at the same time. Try again.")
    return _load(db, session_id, product_id)


def record_waste(
    db: Session, session_id: uuid.UUID, product_id: uuid.UUID, quantity: int
) -> SessionStock:
    session = get_session(db, session_id)
    if session.status == "cancelled":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot record waste on a cancelled session")

    result = db.execute(
        update(SessionStock)
        .where(
            SessionStock.session_id == session_id,
            SessionStock.product_id == product_id,
            AVAILABLE >= quantity,
        )
        .values(wasted_qty=SessionStock.wasted_qty + quantity, updated_at=func.now())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise _shortage(db, session_id, product_id)
    db.commit()
    return _load(db, session_id, product_id)


# ---------------- used by the Orders module (they do NOT commit) ----------------
def reserve_stock(
    db: Session, session_id: uuid.UUID, items: list[tuple[uuid.UUID, int]]
) -> None:
    """Take stock for an order. All items or none.

    Does not commit. The caller owns the transaction, so the order row and the
    stock change succeed or fail together. On any exception, the caller must
    roll back.
    """
    session = get_session(db, session_id)
    if session.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"This stall session is {session.status}"
        )

    wanted = _merge(items)
    # Always lock rows in the same order, so two orders can never deadlock.
    for product_id in sorted(wanted, key=str):
        quantity = wanted[product_id]
        result = db.execute(
            update(SessionStock)
            .where(
                SessionStock.session_id == session_id,
                SessionStock.product_id == product_id,
                AVAILABLE >= quantity,  # checked by PostgreSQL at the moment of update
            )
            .values(sold_qty=SessionStock.sold_qty + quantity, updated_at=func.now())
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise _shortage(db, session_id, product_id)


def release_stock(
    db: Session, session_id: uuid.UUID, items: list[tuple[uuid.UUID, int]]
) -> None:
    """Give stock back when an order is cancelled. Does not commit."""
    wanted = _merge(items)
    for product_id in sorted(wanted, key=str):
        quantity = wanted[product_id]
        result = db.execute(
            update(SessionStock)
            .where(
                SessionStock.session_id == session_id,
                SessionStock.product_id == product_id,
                SessionStock.sold_qty >= quantity,
            )
            .values(sold_qty=SessionStock.sold_qty - quantity, updated_at=func.now())
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Cannot release more stock than was sold"
            )
