from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.expenses.models import Expense
from app.modules.inventory.models import SessionStock
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.stalls.models import StallLocation, StallSession
from app.modules.users.models import User
from scripts import generate_sales_data as gen
from tests.conftest import TestingSession

IST = ZoneInfo("Asia/Kolkata")


def today():
    return datetime.now(IST).date()


def build(days=30, seed=1, customers=10):
    with TestingSession() as db:
        return gen.generate(db, gen.Config(days=days, seed=seed, customers=customers))


def wipe():
    with TestingSession() as db:
        removed = gen.clear_generated(db)
        db.commit()
    return removed


def count(model):
    with TestingSession() as db:
        return db.scalar(select(func.count()).select_from(model))


def snapshot():
    with TestingSession() as db:
        rows = db.execute(
            select(
                StallSession.session_date,
                StallLocation.name,
                Product.name,
                SessionStock.stocked_qty,
                SessionStock.sold_qty,
                SessionStock.wasted_qty,
            )
            .select_from(SessionStock)
            .join(StallSession, StallSession.id == SessionStock.session_id)
            .join(StallLocation, StallLocation.id == StallSession.location_id)
            .join(Product, Product.id == SessionStock.product_id)
            .order_by(StallSession.session_date, StallLocation.name, Product.name)
        ).all()
    return [tuple(row) for row in rows]


# ---------------- consistency ----------------
def test_stock_matches_completed_orders():
    summary = build()
    with TestingSession() as db:
        assert gen.verify(db) == []

    assert summary["sessions"] > 0 and summary["orders_completed"] > 0
    assert summary["units_sold"] > 0
    assert count(StallSession) == summary["sessions"]
    assert count(SessionStock) == summary["stock_rows"]
    assert count(Order) == summary["orders_completed"] + summary["orders_cancelled"]


def test_order_totals_equal_their_items():
    build(days=40)
    with TestingSession() as db:
        totals = dict(db.execute(select(Order.id, Order.total_amount)).all())
        sums = dict(
            db.execute(
                select(OrderItem.order_id, func.sum(OrderItem.quantity * OrderItem.unit_price)).group_by(
                    OrderItem.order_id
                )
            ).all()
        )
    assert totals and totals.keys() == sums.keys()
    assert all(totals[key] == sums[key] for key in totals)


def test_sessions_are_in_the_past_and_closed():
    summary = build()
    with TestingSession() as db:
        sessions = db.scalars(select(StallSession)).all()
    assert all(s.status == "closed" and s.notes == gen.SESSION_MARK for s in sessions)
    assert max(s.session_date for s in sessions) < today()
    assert summary["end"] == (today() - timedelta(days=1)).isoformat()
    with TestingSession() as db:
        statuses = Counter(db.scalars(select(Order.status)).all())
    assert set(statuses) <= {"completed", "cancelled"}


def test_stock_rules_hold_and_data_is_realistic():
    build(days=90, seed=7, customers=20)
    with TestingSession() as db:
        rows = db.execute(
            select(SessionStock.stocked_qty, SessionStock.sold_qty, SessionStock.wasted_qty)
        ).all()
    assert rows
    assert all(sold + wasted <= stocked for stocked, sold, wasted in rows)
    assert any(sold >= stocked for stocked, sold, _ in rows)  # some sell-outs
    assert any(sold < stocked for stocked, sold, _ in rows)  # some leftovers
    assert sum(wasted for *_, wasted in rows) > 0


def test_weekends_sell_more_than_weekdays():
    build(days=90, seed=7, customers=20)
    with TestingSession() as db:
        rows = db.execute(
            select(StallSession.session_date, func.sum(SessionStock.sold_qty))
            .select_from(SessionStock)
            .join(StallSession, StallSession.id == SessionStock.session_id)
            .group_by(StallSession.id, StallSession.session_date)
        ).all()
    weekend = [int(total) for day, total in rows if day.weekday() >= 5]
    weekday = [int(total) for day, total in rows if day.weekday() < 5]
    assert weekend and weekday
    assert sum(weekend) / len(weekend) > 1.4 * sum(weekday) / len(weekday)


def test_expenses_are_generated_and_marked():
    build(days=90, seed=7, customers=20)
    with TestingSession() as db:
        rows = db.execute(
            select(Expense.category, Expense.amount, Expense.session_id, Expense.description, Expense.expense_date)
        ).all()
    assert rows
    assert all(text.startswith(gen.EXPENSE_MARK) and amount > 0 for _, amount, _, text, _ in rows)
    categories = Counter(category for category, *_ in rows)
    assert categories["ingredients"] > 0 and categories["fuel"] > 0
    assert categories["packaging"] > 0 and categories["rent"] >= 2
    assert any(session_id is not None for _, _, session_id, _, _ in rows)
    assert any(session_id is None for _, _, session_id, _, _ in rows)
    assert max(day for *_, day in rows) < today()


# ---------------- markers, reuse and clearing ----------------
def test_everything_is_marked():
    build()
    with TestingSession() as db:
        users = db.scalars(select(User)).all()
        assert users and all(
            u.phone.startswith(gen.PHONE_PREFIX) and not u.is_active and u.role == "customer" for u in users
        )
        assert all(l.google_place_id == gen.LOCATION_MARK for l in db.scalars(select(StallLocation)))
        assert all(p.description == gen.PRODUCT_MARK for p in db.scalars(select(Product)))


def test_clear_removes_generated_rows_only():
    with TestingSession() as db:
        db.add_all(
            [
                User(name="Real Customer", phone="9876543210", password_hash=hash_password("password123"), role="customer"),
                Product(name="Classic Nankhatai", description="real", price=Decimal("130.00"), category="nankhatai"),
                Product(name="Real Cake", price=Decimal("300.00")),
                StallLocation(name="Real Spot", latitude=12.9, longitude=77.5),
            ]
        )
        db.commit()

    summary = build()
    assert summary["products_reused"] == 1 and summary["products_created"] == 5

    with TestingSession() as db:
        real = db.scalars(select(Product).where(Product.name == "Classic Nankhatai")).one()
        assert real.description == "real"  # reused, never marked
        prices = set(
            db.scalars(select(OrderItem.unit_price).where(OrderItem.product_id == real.id)).all()
        )
    assert prices <= {Decimal("130.00"), Decimal("120.00")} and Decimal("130.00") in prices

    removed = wipe()
    assert removed["orders"] > 0 and removed["sessions"] > 0 and removed["users"] == 10

    with TestingSession() as db:
        assert db.scalar(select(func.count()).select_from(Order)) == 0
        assert db.scalar(select(func.count()).select_from(StallSession)) == 0
        assert db.scalar(select(func.count()).select_from(SessionStock)) == 0
        assert db.scalar(select(func.count()).select_from(Expense)) == 0
        assert set(db.scalars(select(Product.name)).all()) == {"Classic Nankhatai", "Real Cake"}
        assert db.scalars(select(User.phone)).all() == ["9876543210"]
        assert db.scalars(select(StallLocation.name)).all() == ["Real Spot"]
        assert gen.generated_exists(db) is False


# ---------------- reproducibility and refusals ----------------
def test_same_seed_gives_the_same_data():
    first_summary = build(seed=3)
    first = snapshot()
    wipe()
    second_summary = build(seed=3)
    second = snapshot()
    assert first == second and first_summary == second_summary

    wipe()
    build(seed=4)
    assert snapshot() != first


def test_second_run_is_refused():
    build()
    with pytest.raises(gen.GeneratedDataExists):
        build()
    wipe()
    build()  # fine again after clearing


@pytest.mark.parametrize(
    "config",
    [
        gen.Config(days=5),
        gen.Config(days=2000),
        gen.Config(customers=2),
        gen.Config(customers=1000),
        gen.Config(end_date=datetime.now(IST).date()),
        gen.Config(end_date=datetime.now(IST).date() + timedelta(days=3)),
    ],
)
def test_bad_settings_write_nothing(config):
    with TestingSession() as db:
        with pytest.raises(ValueError):
            gen.generate(db, config)
    assert count(User) == 0 and count(StallSession) == 0


# ---------------- the whole chain ----------------
def test_generated_history_trains_a_model(tmp_path):
    train = pytest.importorskip("app.ml.train")
    from app.ml import data, features

    build(days=90, seed=7, customers=20)
    with TestingSession() as db:
        frame = data.build_training_frame(db)

    assert len(features.training_rows(frame)) > 200
    result = train.train_and_save(frame, artifact_dir=tmp_path, validation_days=14)
    assert result.model_path.exists()
    assert result.metadata["split"]["train_rows"] >= 50
    assert result.metadata["data"]["series_count"] >= 10
    assert set(result.metadata["validation"]["baselines"]) == {
        "train_mean",
        "previous_day",
        "same_weekday_avg",
        "rolling_7_avg",
    }
