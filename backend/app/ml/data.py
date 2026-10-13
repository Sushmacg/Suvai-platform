"""Reads Suvai's PostgreSQL tables into DataFrames and hands them to features.py.

Run  python -m app.ml.data  to print a summary of the training data.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.ml import features
from app.modules.inventory.models import SessionStock
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.stalls.models import StallLocation, StallSession

HELD_STATUSES = ("open", "closed")  # sessions that actually happened


def load_session_rows(
    db: Session, start: date | None = None, end: date | None = None
) -> pd.DataFrame:
    """One row per product stocked in a session that was opened or closed."""
    # Price the customers really paid: average over orders that were not cancelled.
    line_price = (
        select(
            Order.session_id.label("session_id"),
            OrderItem.product_id.label("product_id"),
            (
                func.sum(OrderItem.quantity * OrderItem.unit_price)
                / func.sum(OrderItem.quantity)
            ).label("avg_price"),
        )
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status != "cancelled")
        .group_by(Order.session_id, OrderItem.product_id)
        .subquery()
    )
    query = (
        select(
            StallSession.session_date.label("date"),
            StallSession.location_id.label("location_id"),
            SessionStock.product_id.label("product_id"),
            Product.category.label("category"),
            Product.price.label("current_price"),
            line_price.c.avg_price.label("avg_price"),
            SessionStock.stocked_qty.label("stocked_qty"),
            SessionStock.wasted_qty.label("wasted_qty"),
            SessionStock.sold_qty.label("units_sold"),
        )
        .select_from(SessionStock)
        .join(StallSession, StallSession.id == SessionStock.session_id)
        .join(Product, Product.id == SessionStock.product_id)
        .outerjoin(
            line_price,
            and_(
                line_price.c.session_id == SessionStock.session_id,
                line_price.c.product_id == SessionStock.product_id,
            ),
        )
        .where(StallSession.status.in_(HELD_STATUSES))
    )
    if start:
        query = query.where(StallSession.session_date >= start)
    if end:
        query = query.where(StallSession.session_date <= end)

    records = [
        {
            "date": row.date,
            "location_id": str(row.location_id),
            "product_id": str(row.product_id),
            "category": row.category,
            "current_price": float(row.current_price),
            "avg_price": np.nan if row.avg_price is None else float(row.avg_price),
            "stocked_qty": row.stocked_qty,
            "wasted_qty": row.wasted_qty,
            "units_sold": row.units_sold,
        }
        for row in db.execute(query)
    ]
    return pd.DataFrame(records, columns=features.RAW_COLUMNS)


def load_products(db: Session) -> pd.DataFrame:
    """Products that are on the menu: id, category and current price."""
    rows = db.execute(
        select(Product.id, Product.category, Product.price).where(Product.is_active.is_(True))
    ).all()
    return pd.DataFrame(
        {
            "product_id": [str(row.id) for row in rows],
            "category": [row.category for row in rows],
            "price": [float(row.price) for row in rows],
        }
    )


def load_location_ids(db: Session) -> list[str]:
    rows = db.scalars(select(StallLocation.id).where(StallLocation.is_active.is_(True))).all()
    return [str(location_id) for location_id in rows]


def build_training_frame(
    db: Session, start: date | None = None, end: date | None = None
) -> pd.DataFrame:
    """Every historical (date, location, product) with its features and its target."""
    daily = features.aggregate_to_daily(load_session_rows(db, start, end))
    return features.build_feature_frame(daily)


def build_prediction_frame(
    db: Session,
    target_date: date,
    location_ids: list[str] | None = None,
    product_ids: list[str] | None = None,
) -> pd.DataFrame:
    """Features for target_date. Only history before that date is read."""
    history = features.aggregate_to_daily(
        load_session_rows(db, end=target_date - timedelta(days=1))
    )
    products = load_products(db)
    if product_ids is not None:
        wanted = [str(p) for p in product_ids]
        products = products[products["product_id"].isin(wanted)]
    locations = [str(x) for x in location_ids] if location_ids is not None else load_location_ids(db)
    return features.build_prediction_features(history, target_date, locations, products)


def _preview() -> None:
    from app.db.session import SessionLocal

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 60)
    with SessionLocal() as db:
        frame = build_training_frame(db)

    if frame.empty:
        print("No data yet. Training rows come from stock that was set for a session")
        print("which has been opened or closed.")
        return

    print(f"Rows (date x location x product): {len(frame)}")
    print(f"Dates: {frame['date'].min().date()} to {frame['date'].max().date()}")
    print(f"Series (location x product): {frame.groupby(features.SERIES_KEYS).ngroups}")
    target = frame[features.TARGET]
    print(
        f"Target {features.TARGET}: mean {target.mean():.2f}, "
        f"min {target.min():.0f}, max {target.max():.0f}"
    )
    print(f"Rows that sold out (true demand was higher): {int(frame['was_sold_out'].sum())}")

    missing = frame[features.FEATURE_COLUMNS].isna().sum()
    missing = missing[missing > 0]
    print("\nMissing values per feature, before imputation:")
    print("none" if missing.empty else missing.to_string())

    sample = frame[
        ["date", "location_id", "product_id", features.TARGET, "lag_1", "rolling_mean_7", "n_prior_days"]
    ].head(10)
    sample = sample.assign(
        location_id=sample["location_id"].str[:8], product_id=sample["product_id"].str[:8]
    )
    print("\nSample rows:")
    print(sample.to_string(index=False))


if __name__ == "__main__":
    _preview()
