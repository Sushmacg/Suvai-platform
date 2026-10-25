from datetime import timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.modules.expenses.models import Expense
from app.modules.inventory.models import SessionStock
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.stalls.models import StallLocation, StallSession
from app.modules.stalls.service import today_ist


def _start(days: int):
    return today_ist() - timedelta(days=days - 1)


def summary(db: Session, days: int) -> dict:
    start = _start(days)
    revenue, orders = db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0), func.count(Order.id))
        .select_from(Order)
        .join(StallSession, StallSession.id == Order.session_id)
        .where(Order.status == "completed", StallSession.session_date >= start)
    ).one()
    expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.expense_date >= start)
    )
    stocked, sold, wasted = db.execute(
        select(
            func.coalesce(func.sum(SessionStock.stocked_qty), 0),
            func.coalesce(func.sum(SessionStock.sold_qty), 0),
            func.coalesce(func.sum(SessionStock.wasted_qty), 0),
        )
        .select_from(SessionStock)
        .join(StallSession, StallSession.id == SessionStock.session_id)
        .where(StallSession.session_date >= start)
    ).one()
    return {
        "from": start.isoformat(),
        "to": today_ist().isoformat(),
        "revenue": float(revenue),
        "orders": int(orders),
        "expenses": float(expenses),
        "profit": float(revenue - expenses),
        "stocked": int(stocked),
        "sold": int(sold),
        "wasted": int(wasted),
        "sell_through": round(int(sold) / int(stocked), 3) if stocked else 0,
    }


def sales(db: Session, days: int) -> list[dict]:
    rows = db.execute(
        select(StallSession.session_date, func.sum(Order.total_amount), func.count(Order.id))
        .select_from(Order)
        .join(StallSession, StallSession.id == Order.session_id)
        .where(Order.status == "completed", StallSession.session_date >= _start(days))
        .group_by(StallSession.session_date)
        .order_by(StallSession.session_date)
    ).all()
    return [{"date": d.isoformat(), "revenue": float(r), "orders": int(n)} for d, r, n in rows]


def products(db: Session, days: int, limit: int) -> list[dict]:
    units = func.sum(OrderItem.quantity)
    rows = db.execute(
        select(Product.name, units, func.sum(OrderItem.quantity * OrderItem.unit_price))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(StallSession, StallSession.id == Order.session_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(Order.status == "completed", StallSession.session_date >= _start(days))
        .group_by(Product.id, Product.name)
        .order_by(desc(units))
        .limit(limit)
    ).all()
    return [{"name": n, "units": int(u), "revenue": float(r)} for n, u, r in rows]


def locations(db: Session, days: int) -> list[dict]:
    revenue = func.sum(Order.total_amount)
    rows = db.execute(
        select(StallLocation.name, revenue, func.count(Order.id))
        .select_from(Order)
        .join(StallSession, StallSession.id == Order.session_id)
        .join(StallLocation, StallLocation.id == StallSession.location_id)
        .where(Order.status == "completed", StallSession.session_date >= _start(days))
        .group_by(StallLocation.id, StallLocation.name)
        .order_by(desc(revenue))
    ).all()
    return [{"name": n, "revenue": float(r), "orders": int(c)} for n, r, c in rows]