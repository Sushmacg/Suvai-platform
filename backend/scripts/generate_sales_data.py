"""Generate realistic past sales so the ML pipeline has history to learn from.

Run from the backend folder:

    python -m scripts.generate_sales_data            # 180 days ending yesterday
    python -m scripts.generate_sales_data --reset    # remove generated rows, then generate again
    python -m scripts.generate_sales_data --clear    # remove generated rows and stop

Rows are written straight into the real tables (the API refuses past dates).
Every generated row is marked, so --clear removes exactly those rows:

    users      phone starts with 0000, inactive, cannot log in
    locations  google_place_id = "generated-data"
    sessions   notes = "generated-data"
    products   description = "GENERATED-DATA" (products that already exist by name are reused, never marked)
    expenses   description starts with "[generated] "
    orders     belong to generated customers

This is GENERATED data. Results from it show that the pipeline works, not how real
customers behave. Festival dates below are approximate. Check a calendar.
"""
from __future__ import annotations

import argparse
import secrets
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import app.db.all_models  # noqa: F401  (registers every model)
from app.core.security import hash_password
from app.modules.expenses.models import Expense
from app.modules.inventory.models import SessionStock
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.reviews.models import Review
from app.modules.stalls.models import StallLocation, StallSession
from app.modules.users.models import User

IST = ZoneInfo("Asia/Kolkata")
CENTS = Decimal("0.01")
ZERO = Decimal("0.00")

PHONE_PREFIX = "0000"  # cannot be a real Indian mobile number
LOCATION_MARK = "generated-data"
SESSION_MARK = "generated-data"
PRODUCT_MARK = "GENERATED-DATA"
EXPENSE_MARK = "[generated] "

GIFT_BOX = "Gift Box (12 pcs)"
TREND_GROWTH = 0.20  # demand grows 20% over the period

PRODUCTS = [
    # name, category, current price, units per visit at a neutral location
    ("Classic Nankhatai", "nankhatai", Decimal("120"), 14.0),
    ("Elaichi Nankhatai", "nankhatai", Decimal("150"), 9.0),
    ("Ajwain Nankhatai", "savoury", Decimal("110"), 5.0),
    ("Dry Fruit Nankhatai", "nankhatai", Decimal("220"), 6.0),
    ("Jaggery Nankhatai", "nankhatai", Decimal("140"), 4.0),
    (GIFT_BOX, "gift", Decimal("450"), 2.0),
]

LOCATIONS = [
    # name, address, latitude, longitude, demand factor (coordinates are approximate)
    ("Market Gate", "Main Market, Hassan", 13.0068, 76.0996, 1.35),
    ("Tech Park Junction", "Tech Park Road, Hassan", 13.0125, 76.1150, 0.95),
    ("Hassan Bus Stand", "KSRTC Bus Stand, Hassan", 13.0033, 76.1004, 0.85),
    ("Lake Road Park", "Lake Road, Hassan", 12.9962, 76.0890, 1.05),
]

# (product, location) -> demand multiplier. 0 means the product is not carried there.
AFFINITY = {
    (GIFT_BOX, "Tech Park Junction"): 0.0,
    (GIFT_BOX, "Hassan Bus Stand"): 0.0,
    (GIFT_BOX, "Market Gate"): 1.8,
    ("Jaggery Nankhatai", "Market Gate"): 1.4,
    ("Dry Fruit Nankhatai", "Tech Park Junction"): 1.3,
    ("Ajwain Nankhatai", "Hassan Bus Stand"): 1.5,
    ("Classic Nankhatai", "Lake Road Park"): 1.1,
}

# weekday (Monday = 0) -> [(location, start, end, chance the stall goes)]
SCHEDULE = {
    0: [("Tech Park Junction", time(11, 30), time(15, 0), 0.65)],
    1: [("Hassan Bus Stand", time(16, 0), time(20, 30), 0.90)],
    2: [
        ("Tech Park Junction", time(11, 30), time(15, 0), 0.90),
        ("Lake Road Park", time(17, 0), time(20, 30), 0.35),
    ],
    3: [("Hassan Bus Stand", time(16, 0), time(20, 30), 0.90)],
    4: [
        ("Tech Park Junction", time(11, 30), time(15, 0), 0.90),
        ("Lake Road Park", time(17, 0), time(20, 30), 0.45),
    ],
    5: [("Market Gate", time(10, 0), time(21, 0), 0.92)],
    6: [("Market Gate", time(10, 0), time(21, 0), 0.88)],
}
WEEKDAY_FACTOR = [0.90, 0.90, 0.95, 1.00, 1.15, 1.45, 1.30]

FESTIVAL_DATES = {  # approximate 2026 dates
    date(2026, 5, 27),
    date(2026, 8, 15),
    date(2026, 8, 26),
    date(2026, 8, 28),
    date(2026, 9, 14),
    date(2026, 10, 2),
    date(2026, 10, 20),
    date(2026, 11, 8),
}

BASKET_SIZES = np.array([1, 2, 3, 4, 5, 6])
BASKET_PROBS = [0.25, 0.30, 0.20, 0.12, 0.08, 0.05]


class GeneratedDataExists(RuntimeError):
    """Generated rows are already in the database. Use --reset."""


@dataclass(frozen=True)
class Config:
    days: int = 180
    end_date: date | None = None  # last session day. Default: yesterday (India time)
    seed: int = 42
    customers: int = 60


@dataclass
class Day:
    when: date
    weekday: int
    trend: float
    fest: float
    payday: float
    weather: float
    price_effect: float
    prices: dict


@dataclass
class Ctx:
    db: Session
    rng: np.random.Generator
    days: int
    start: date
    rise_day: date
    customers: list
    weights: np.ndarray
    locations: dict
    products: list
    names: dict
    totals: dict


# ---------------------------------------------------------------- small helpers
def today_ist() -> date:
    return datetime.now(IST).date()


def new_id(rng: np.random.Generator) -> uuid.UUID:
    """Ids come from the seeded generator, so the same seed gives the same ids."""
    return uuid.UUID(bytes=bytes(rng.bytes(16)), version=4)


def stamp(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour, 0), tzinfo=IST)


def money(value: float) -> Decimal:
    return Decimal(f"{value:.2f}")


def festival_factor(day: date) -> float:
    if day in FESTIVAL_DATES:
        return 1.6
    if day + timedelta(days=1) in FESTIVAL_DATES:
        return 1.3  # the day before
    if day - timedelta(days=1) in FESTIVAL_DATES:
        return 1.1  # the day after
    return 1.0


def price_on(day: date, current: Decimal, rise_day: date) -> Decimal:
    """Prices rose 8% on rise_day. Before it, they were lower (whole rupees)."""
    if day >= rise_day:
        return current
    old = (current / Decimal("1.08")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(old, Decimal("1")).quantize(CENTS)


def split_into_baskets(rng: np.random.Generator, sold: dict) -> list[dict]:
    """Share sold units out between customers. Every unit ends up in exactly one basket."""
    pool = [product_id for product_id, qty in sold.items() for _ in range(qty)]
    if not pool:
        return []
    pool = [pool[int(i)] for i in rng.permutation(len(pool))]
    baskets, index = [], 0
    while index < len(pool):
        size = int(rng.choice(BASKET_SIZES, p=BASKET_PROBS))
        basket: dict = {}
        for product_id in pool[index : index + size]:
            basket[product_id] = basket.get(product_id, 0) + 1
        baskets.append(basket)
        index += size
    return baskets


def _validate(config: Config, today: date) -> None:
    if not 14 <= config.days <= 730:
        raise ValueError("days must be between 14 and 730")
    if not 5 <= config.customers <= 500:
        raise ValueError("customers must be between 5 and 500")
    if config.end_date is not None and config.end_date >= today:
        raise ValueError("end_date must be before today")


# ---------------------------------------------------------------- generated rows
def generated_exists(db: Session) -> bool:
    checks = [
        select(User.id).where(User.phone.startswith(PHONE_PREFIX)),
        select(StallSession.id).where(StallSession.notes == SESSION_MARK),
        select(StallLocation.id).where(StallLocation.google_place_id == LOCATION_MARK),
        select(Product.id).where(Product.description == PRODUCT_MARK),
        select(Expense.id).where(Expense.description.startswith(EXPENSE_MARK)),
    ]
    return any(db.scalar(query.limit(1)) is not None for query in checks)


def clear_generated(db: Session) -> dict[str, int]:
    """Delete generated rows only. Does not commit."""
    generated_users = select(User.id).where(
        User.phone.startswith(PHONE_PREFIX), User.role == "customer"
    )
    generated_orders = select(Order.id).where(Order.customer_id.in_(generated_users))
    has_orders = select(Order.id).where(Order.session_id == StallSession.id).exists()
    deletable_sessions = select(StallSession.id).where(
        StallSession.notes == SESSION_MARK, ~has_orders
    )

    removed: dict[str, int] = {}
    removed["order_items"] = db.execute(
        delete(OrderItem).where(OrderItem.order_id.in_(generated_orders))
    ).rowcount
    removed["orders"] = db.execute(
        delete(Order).where(Order.customer_id.in_(generated_users))
    ).rowcount
    removed["expenses"] = db.execute(
        delete(Expense).where(Expense.description.startswith(EXPENSE_MARK))
    ).rowcount
    removed["stock_rows"] = db.execute(
        delete(SessionStock).where(SessionStock.session_id.in_(deletable_sessions))
    ).rowcount
    removed["sessions"] = db.execute(
        delete(StallSession).where(StallSession.notes == SESSION_MARK, ~has_orders)
    ).rowcount
    removed["locations"] = db.execute(
        delete(StallLocation).where(
            StallLocation.google_place_id == LOCATION_MARK,
            ~select(StallSession.id).where(StallSession.location_id == StallLocation.id).exists(),
        )
    ).rowcount
    removed["products"] = db.execute(
        delete(Product).where(
            Product.description == PRODUCT_MARK,
            ~select(OrderItem.id).where(OrderItem.product_id == Product.id).exists(),
            ~select(SessionStock.id).where(SessionStock.product_id == Product.id).exists(),
            ~select(Review.id).where(Review.product_id == Product.id).exists(),
        )
    ).rowcount
    removed["users"] = db.execute(
        delete(User).where(
            User.phone.startswith(PHONE_PREFIX),
            User.role == "customer",
            ~select(Order.id).where(Order.customer_id == User.id).exists(),
        )
    ).rowcount
    return removed


def verify(db: Session) -> list[str]:
    """Stock sold_qty must equal the units in completed orders, for every generated session."""
    sessions = select(StallSession.id).where(StallSession.notes == SESSION_MARK)
    in_stock = {
        (row[0], row[1]): int(row[2])
        for row in db.execute(
            select(SessionStock.session_id, SessionStock.product_id, SessionStock.sold_qty).where(
                SessionStock.session_id.in_(sessions)
            )
        )
    }
    in_orders = {
        (row[0], row[1]): int(row[2])
        for row in db.execute(
            select(Order.session_id, OrderItem.product_id, func.sum(OrderItem.quantity))
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.status == "completed", Order.session_id.in_(sessions))
            .group_by(Order.session_id, OrderItem.product_id)
        )
    }
    problems = []
    for key in sorted(set(in_stock) | set(in_orders), key=str):
        if in_stock.get(key, 0) != in_orders.get(key, 0):
            problems.append(
                f"session {key[0]} product {key[1]}: stock sold {in_stock.get(key, 0)}, "
                f"completed orders {in_orders.get(key, 0)}"
            )
    return problems


# ------------------------------------------------------------------- generation
def _add_expense(ctx: Ctx, amount: Decimal, category: str, text: str, day: date, session_id=None):
    when = stamp(day, 12)
    ctx.db.add(
        Expense(
            id=new_id(ctx.rng),
            amount=amount,
            category=category,
            description=EXPENSE_MARK + text,
            expense_date=day,
            session_id=session_id,
            created_by=None,
            created_at=when,
            updated_at=when,
        )
    )
    ctx.totals["expenses"] += 1
    ctx.totals["expenses_total"] += amount


def _generate_session(ctx: Ctx, d: Day, loc_name: str, start_t: time, end_t: time) -> None:
    rng, db = ctx.rng, ctx.db
    location, loc_factor = ctx.locations[loc_name]

    session = StallSession(
        id=new_id(rng),
        location_id=location.id,
        session_date=d.when,
        start_time=start_t,
        end_time=end_t,
        status="closed",
        notes=SESSION_MARK,
        created_at=stamp(d.when - timedelta(days=1), 20),
    )
    db.add(session)
    db.flush()
    ctx.totals["sessions"] += 1

    session_noise = float(rng.lognormal(0.0, 0.12))
    sold: dict = {}
    stock_rows = []
    stocked_value = ZERO

    for product, base in ctx.products:
        affinity = AFFINITY.get((product.name, loc_name), 1.0)
        if affinity == 0 or rng.random() < 0.05:  # not carried, or ran out of ingredients
            continue
        gift = 2.0 if product.name == GIFT_BOX and d.fest >= 1.3 else 1.0
        # What the admin can predict.
        known = (
            base * loc_factor * affinity * WEEKDAY_FACTOR[d.weekday]
            * d.trend * d.fest * gift * d.payday
        )
        stocked = max(3, int(round(known * rng.uniform(0.95, 1.5))))
        # What the admin cannot predict: weather, the day's crowd, random buying.
        lam = known * d.weather * session_noise * d.price_effect
        demand = int(rng.poisson(lam * rng.gamma(8.0, 1.0 / 8.0)))

        units = min(demand, stocked)
        leftover = stocked - units
        wasted = 0
        if leftover:
            wasted = min(leftover, int(round(leftover * rng.uniform(0.4, 1.0))))

        stock_rows.append(
            SessionStock(
                id=new_id(rng),
                session_id=session.id,
                product_id=product.id,
                stocked_qty=stocked,
                sold_qty=units,
                wasted_qty=wasted,
                min_stock=int(round(stocked * 0.15)),
                created_at=session.created_at,
                updated_at=stamp(d.when, 22),
            )
        )
        stocked_value += d.prices[product.id] * stocked
        if units > 0:
            sold[product.id] = units
        ctx.totals["stock_rows"] += 1
        ctx.totals["units_sold"] += units
        ctx.totals["units_wasted"] += wasted
        if demand >= stocked:
            ctx.totals["sold_out_rows"] += 1

    db.add_all(stock_rows)
    db.flush()

    # Orders: completed baskets hold exactly the sold units. Cancelled ones are extra
    # baskets whose stock was given back, so they never count as sold.
    baskets = split_into_baskets(rng, sold)
    stocked_ids = [row.product_id for row in stock_rows]
    cancelled: list[dict] = []
    if stocked_ids:
        for _ in range(int(rng.poisson(0.03 * len(baskets)))):
            how_many = min(int(rng.integers(1, 3)), len(stocked_ids))
            chosen = rng.choice(len(stocked_ids), size=how_many, replace=False)
            cancelled.append(
                {stocked_ids[int(i)]: int(rng.integers(1, 4)) for i in chosen}
            )

    work = [(b, "completed") for b in baskets] + [(b, "cancelled") for b in cancelled]
    if work:
        picks = rng.choice(len(ctx.customers), size=len(work), p=ctx.weights)
        span = (end_t.hour * 60 + end_t.minute) - (start_t.hour * 60 + start_t.minute)
        orders, items = [], []
        for (basket, status), pick in zip(work, picks):
            order_id = new_id(rng)
            created = datetime.combine(d.when, start_t, tzinfo=IST) + timedelta(
                minutes=float(rng.uniform(0, span))
            )
            total = ZERO
            for product_id, qty in basket.items():
                unit_price = d.prices[product_id]
                items.append(
                    OrderItem(
                        id=new_id(rng),
                        order_id=order_id,
                        product_id=product_id,
                        product_name=ctx.names[product_id],
                        quantity=qty,
                        unit_price=unit_price,
                    )
                )
                total += unit_price * qty
            total = total.quantize(CENTS)
            orders.append(
                Order(
                    id=order_id,
                    customer_id=ctx.customers[int(pick)].id,
                    session_id=session.id,
                    status=status,
                    total_amount=total,
                    notes=None,
                    created_at=created,
                    updated_at=created + timedelta(minutes=int(rng.integers(3, 25))),
                )
            )
            if status == "completed":
                ctx.totals["orders_completed"] += 1
                ctx.totals["revenue"] += total
            else:
                ctx.totals["orders_cancelled"] += 1
        db.add_all(orders)
        db.flush()
        db.add_all(items)
        db.flush()

    # Expenses tied to this session.
    if stocked_value > 0:
        share = Decimal(str(round(float(rng.uniform(0.32, 0.42)), 4)))
        _add_expense(
            ctx,
            (stocked_value * share).quantize(CENTS, rounding=ROUND_HALF_UP),
            "ingredients",
            f"Ingredients for {loc_name}",
            d.when - timedelta(days=1),
            session.id,
        )
    _add_expense(ctx, money(rng.uniform(70, 160)), "fuel", f"Fuel for {loc_name}", d.when, session.id)
    if d.weekday >= 5:
        _add_expense(ctx, Decimal("400.00"), "labour", f"Weekend helper at {loc_name}", d.when, session.id)


def _daily_expenses(ctx: Ctx, d: Day) -> None:
    rng = ctx.rng
    if d.weekday == 0:
        _add_expense(ctx, money(rng.uniform(300, 500)), "packaging", "Weekly packaging", d.when)
    if d.when.day == 1:
        _add_expense(ctx, Decimal("4000.00"), "rent", "Monthly stall rent", d.when)
    if rng.random() < 0.02:
        _add_expense(ctx, money(rng.uniform(500, 1500)), "marketing", "Flyers and offers", d.when)
    if rng.random() < 0.01:
        _add_expense(ctx, money(rng.uniform(200, 900)), "maintenance", "Stall repair", d.when)


def generate(db: Session, config: Config) -> dict[str, Any]:
    """Write generated history in ONE transaction: all of it, or nothing."""
    today = today_ist()
    _validate(config, today)
    if generated_exists(db):
        raise GeneratedDataExists(
            "Generated data is already in the database. Use --reset to replace it."
        )

    end = config.end_date or today - timedelta(days=1)
    start = end - timedelta(days=config.days - 1)
    rise_day = start + timedelta(days=int(config.days * 0.6))
    rng = np.random.default_rng(config.seed)

    try:
        shared_hash = hash_password(secrets.token_urlsafe(24))  # random, so nobody can log in
        customers = [
            User(
                id=new_id(rng),
                name=f"Generated Customer {index:03d}",
                phone=f"{PHONE_PREFIX}{index:06d}",
                email=None,
                password_hash=shared_hash,
                role="customer",
                is_active=False,
            )
            for index in range(1, config.customers + 1)
        ]
        weights = 1.0 / np.arange(1, config.customers + 1) ** 0.7  # a few regulars, many occasional
        weights = weights / weights.sum()

        locations = {}
        for name, address, lat, lng, factor in LOCATIONS:
            location = StallLocation(
                id=new_id(rng),
                name=name,
                address=address,
                latitude=lat,
                longitude=lng,
                google_place_id=LOCATION_MARK,
                is_active=True,
            )
            locations[name] = (location, factor)

        existing = {
            p.name: p
            for p in db.scalars(select(Product).where(Product.name.in_([row[0] for row in PRODUCTS])))
        }
        products, created_products = [], 0
        for name, category, price, base in PRODUCTS:
            product = existing.get(name)
            if product is None:
                product = Product(
                    id=new_id(rng),
                    name=name,
                    description=PRODUCT_MARK,
                    category=category,
                    price=price.quantize(CENTS),
                    is_available=True,
                    is_active=True,
                )
                db.add(product)
                created_products += 1
            products.append((product, base))

        db.add_all(customers)
        db.add_all([location for location, _ in locations.values()])
        db.flush()

        totals: dict[str, Any] = defaultdict(int)
        totals["revenue"] = ZERO
        totals["expenses_total"] = ZERO
        ctx = Ctx(
            db=db,
            rng=rng,
            days=config.days,
            start=start,
            rise_day=rise_day,
            customers=customers,
            weights=weights,
            locations=locations,
            products=products,
            names={product.id: product.name for product, _ in products},
            totals=totals,
        )

        for offset in range(config.days):
            when = start + timedelta(days=offset)
            day = Day(
                when=when,
                weekday=when.weekday(),
                trend=1.0 + TREND_GROWTH * offset / max(config.days - 1, 1),
                fest=festival_factor(when),
                payday=1.08 if when.day <= 7 else 1.0,
                weather=0.6 if rng.random() < 0.08 else 1.0,  # a rainy day
                price_effect=1.03 if when < rise_day else 1.0,
                prices={
                    product.id: price_on(when, product.price, rise_day) for product, _ in products
                },
            )
            for loc_name, start_t, end_t, chance in SCHEDULE[day.weekday]:
                if rng.random() < chance:
                    _generate_session(ctx, day, loc_name, start_t, end_t)
            _daily_expenses(ctx, day)

        db.commit()
    except Exception:
        db.rollback()
        raise

    summary = dict(totals)
    summary.update(
        start=start.isoformat(),
        end=end.isoformat(),
        days=config.days,
        seed=config.seed,
        customers=config.customers,
        locations=len(LOCATIONS),
        products_created=created_products,
        products_reused=len(PRODUCTS) - created_products,
    )
    return summary


# ------------------------------------------------------------------------- CLI
def format_summary(s: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Generated sales data (marked as generated, remove with --clear)",
            f"  period:            {s['start']} to {s['end']} ({s['days']} days, seed {s['seed']})",
            f"  customers:         {s['customers']}",
            f"  locations:         {s['locations']}",
            f"  products:          {s['products_created']} created, {s['products_reused']} reused",
            f"  sessions:          {s['sessions']}",
            f"  stock rows:        {s['stock_rows']} (sold out: {s['sold_out_rows']})",
            f"  units sold/wasted: {s['units_sold']} / {s['units_wasted']}",
            f"  orders:            {s['orders_completed']} completed, {s['orders_cancelled']} cancelled",
            f"  revenue:           Rs. {s['revenue']:,.2f}",
            f"  expenses:          {s['expenses']} rows, Rs. {s['expenses_total']:,.2f}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate marked, removable sales history.")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--end-date", type=date.fromisoformat, default=None, help="YYYY-MM-DD, before today")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=60)
    parser.add_argument("--reset", action="store_true", help="remove generated rows, then generate again")
    parser.add_argument("--clear", action="store_true", help="remove generated rows and stop")
    args = parser.parse_args(argv)

    from app.db.session import SessionLocal, engine

    database = engine.url.database or ""
    print(f"Database: {database}")
    if database.endswith("_test"):
        print("Refusing to write into a test database.")
        return 1

    config = Config(days=args.days, end_date=args.end_date, seed=args.seed, customers=args.customers)
    with SessionLocal() as db:
        if args.clear or args.reset:
            removed = clear_generated(db)
            db.commit()
            print("Removed generated rows: " + ", ".join(f"{k} {v}" for k, v in removed.items()))
            if args.clear:
                return 0
        try:
            summary = generate(db, config)
        except GeneratedDataExists as error:
            print(error)
            return 1
        except ValueError as error:
            print(f"Invalid options: {error}")
            return 1
        problems = verify(db)

    print(format_summary(summary))
    if problems:
        print(f"Consistency check FAILED ({len(problems)} problems):")
        for line in problems[:10]:
            print(f"  {line}")
        return 1
    print("Consistency check: OK (stock sold equals completed order units)")
    print("\nNext:\n  python -m app.ml.data\n  python -m app.ml.train --no-refit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
