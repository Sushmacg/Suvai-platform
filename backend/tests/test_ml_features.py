from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from app.ml import data, features
from tests.conftest import PREFIX, TestingSession

IST = ZoneInfo("Asia/Kolkata")
LOCATIONS = ["loc-a", "loc-b"]
PRODUCTS = pd.DataFrame(
    {
        "product_id": ["prod-1", "prod-2"],
        "category": ["nankhatai", "nankhatai"],
        "price": [120.0, 150.0],
    }
)


# ---------------- helpers ----------------
def daily_frame(rows, location="loc-a", product="prod-1", price=100.0):
    """rows = [(date string, units sold), ...] for one location and product."""
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp(day),
                "location_id": location,
                "product_id": product,
                "category": "nankhatai",
                "price": price,
                "stocked_qty": units + 1.0,
                "wasted_qty": 0.0,
                "was_sold_out": 0.0,
                "units_sold": float(units),
            }
            for day, units in rows
        ]
    )


def synthetic_daily(days=21):
    """Two locations x two products. loc-b is not visited on every day."""
    start = pd.Timestamp("2026-09-01")
    rows = []
    for offset in range(days):
        day = start + pd.Timedelta(days=offset)
        for location, boost in (("loc-a", 3), ("loc-b", 0)):
            if location == "loc-b" and offset % 3 == 1 and offset != days - 1:
                continue
            for product, base, price in (("prod-1", 10, 120.0), ("prod-2", 4, 150.0)):
                units = base + boost + day.day_of_week
                rows.append(
                    {
                        "date": day,
                        "location_id": location,
                        "product_id": product,
                        "category": "nankhatai",
                        "price": price,
                        "stocked_qty": units + 2.0,
                        "wasted_qty": 0.0,
                        "was_sold_out": 0.0,
                        "units_sold": float(units),
                    }
                )
    return pd.DataFrame(rows)


def values(frame, column):
    return frame[column].to_numpy(dtype=float)


# ---------------- calendar ----------------
def test_calendar_features():
    frame = features.add_calendar_features(
        pd.DataFrame({"date": pd.to_datetime(["2026-10-12", "2026-10-17"])})
    )
    monday, saturday = frame.iloc[0], frame.iloc[1]

    assert (monday["day_of_week"], monday["is_weekend"]) == (0, 0)
    assert (monday["month"], monday["day_of_month"], monday["week_of_year"]) == (10, 12, 42)
    assert monday["dow_sin"] == pytest.approx(0.0)
    assert monday["dow_cos"] == pytest.approx(1.0)
    assert (saturday["day_of_week"], saturday["is_weekend"]) == (5, 1)
    assert monday["month_sin"] == pytest.approx(np.sin(2 * np.pi * 9 / 12))


# ---------------- history features ----------------
def test_history_features_use_only_earlier_days():
    frame = features.build_feature_frame(
        daily_frame([("2026-10-01", 10), ("2026-10-02", 20), ("2026-10-04", 30), ("2026-10-05", 40)])
    )
    nan = np.nan

    np.testing.assert_allclose(values(frame, "lag_1"), [nan, 10, 20, 30])
    np.testing.assert_allclose(values(frame, "lag_2"), [nan, nan, 10, 20])
    np.testing.assert_allclose(values(frame, "rolling_mean_3"), [nan, 10, 15, 20])
    np.testing.assert_allclose(values(frame, "rolling_mean_7"), [nan, 10, 15, 20])
    np.testing.assert_allclose(values(frame, "expanding_mean"), [nan, 10, 15, 20])
    np.testing.assert_allclose(values(frame, "rolling_std_7"), [nan, nan, 7.0710678, 10.0])
    np.testing.assert_allclose(values(frame, "n_prior_days"), [0, 1, 2, 3])
    np.testing.assert_allclose(values(frame, "days_since_last_stocked"), [nan, 1, 2, 1])
    np.testing.assert_allclose(values(frame, "product_avg_prior"), [nan, 10, 15, 20])


def test_same_weekday_features():
    mondays = ["2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26"]
    frame = features.build_feature_frame(daily_frame(list(zip(mondays, [10, 20, 30, 40]))))
    nan = np.nan

    np.testing.assert_allclose(values(frame, "same_weekday_lag_1"), [nan, 10, 20, 30])
    np.testing.assert_allclose(values(frame, "same_weekday_mean_4"), [nan, 10, 15, 20])
    np.testing.assert_allclose(values(frame, "days_since_last_stocked"), [nan, 7, 7, 7])


def test_sold_out_rate_counts_only_earlier_days():
    daily = daily_frame([("2026-10-01", 10), ("2026-10-02", 10), ("2026-10-03", 10)])
    daily["was_sold_out"] = [1.0, 0.0, 1.0]
    frame = features.build_feature_frame(daily)

    np.testing.assert_allclose(
        values(frame, "prior_sold_out_rate_7"), [np.nan, 1.0, 0.5]
    )


def test_cross_series_averages_exclude_the_same_day():
    daily = pd.concat(
        [
            daily_frame([("2026-10-01", 10), ("2026-10-02", 100)], location="loc-a"),
            daily_frame([("2026-10-01", 30), ("2026-10-02", 100)], location="loc-b"),
        ],
        ignore_index=True,
    )
    frame = features.build_feature_frame(daily)
    first = frame[frame["date"] == "2026-10-01"]
    second = frame[frame["date"] == "2026-10-02"].set_index("location_id")

    assert first["product_avg_prior"].isna().all()  # nothing earlier, and not the other location today
    assert second["product_avg_prior"].tolist() == [20.0, 20.0]  # mean of 10 and 30
    assert second.loc["loc-a", "location_avg_prior"] == 10.0
    assert second.loc["loc-b", "location_avg_prior"] == 30.0


# ---------------- leakage ----------------
def test_changing_the_future_never_changes_earlier_features():
    daily = synthetic_daily()
    pivot = pd.Timestamp("2026-09-11")

    changed = daily.copy()
    later = changed["date"] >= pivot
    changed.loc[later, "units_sold"] = changed.loc[later, "units_sold"] * 100
    changed.loc[later, "was_sold_out"] = 1.0

    before = features.build_feature_frame(daily)
    after = features.build_feature_frame(changed)

    # up to and including the pivot day, no feature may notice the change
    keep_before = before[before["date"] <= pivot][features.FEATURE_COLUMNS]
    keep_after = after[after["date"] <= pivot][features.FEATURE_COLUMNS]
    pd.testing.assert_frame_equal(keep_before, keep_after, check_dtype=False)

    # sanity check: days after the pivot do react to it
    later_before = before[before["date"] > pivot][features.HISTORY_FEATURES]
    later_after = after[after["date"] > pivot][features.HISTORY_FEATURES]
    assert not later_before.equals(later_after)


def test_target_and_same_day_columns_are_never_features():
    forbidden = {features.TARGET, *features.METADATA_COLUMNS}
    assert not forbidden & set(features.FEATURE_COLUMNS)

    X, y = features.split_features_target(features.build_feature_frame(synthetic_daily()))
    assert list(X.columns) == features.FEATURE_COLUMNS
    assert not forbidden & set(X.columns)
    assert y.name == features.TARGET and len(X) == len(y)


# ---------------- prediction ----------------
def test_prediction_features_match_training_features():
    daily = synthetic_daily()
    training = features.build_feature_frame(daily)
    last_day = daily["date"].max()

    prediction = features.build_prediction_features(
        daily[daily["date"] < last_day], last_day, LOCATIONS, PRODUCTS
    )

    expected = (
        training[training["date"] == last_day]
        .sort_values(features.SERIES_KEYS)
        .reset_index(drop=True)
    )
    actual = prediction.sort_values(features.SERIES_KEYS).reset_index(drop=True)

    assert len(expected) == len(actual) == 4
    pd.testing.assert_frame_equal(
        actual[features.FEATURE_COLUMNS], expected[features.FEATURE_COLUMNS], check_dtype=False
    )
    assert actual[features.TARGET].isna().all()


def test_prediction_ignores_rows_on_or_after_the_target_date():
    daily = synthetic_daily()
    target = daily["date"].max()
    after_target = daily[daily["date"] == target].copy()
    after_target["date"] = target + pd.Timedelta(days=2)

    clean = features.build_prediction_features(
        daily[daily["date"] < target], target, LOCATIONS, PRODUCTS
    )
    with_extras = features.build_prediction_features(
        pd.concat([daily, after_target], ignore_index=True), target, LOCATIONS, PRODUCTS
    )

    pd.testing.assert_frame_equal(clean, with_extras, check_dtype=False)


def test_a_new_product_gets_cold_start_features_and_can_be_encoded():
    daily = synthetic_daily()
    last_day = daily["date"].max()
    products = pd.concat(
        [
            PRODUCTS,
            pd.DataFrame({"product_id": ["prod-new"], "category": ["savoury"], "price": [99.0]}),
        ],
        ignore_index=True,
    )

    prediction = features.build_prediction_features(
        daily[daily["date"] < last_day], last_day, LOCATIONS, products
    )
    fresh = prediction[prediction["product_id"] == "prod-new"]

    assert len(fresh) == 2  # one per location
    assert (fresh["n_prior_days"] == 0).all()
    assert fresh[["lag_1", "lag_2", "rolling_mean_7", "product_avg_prior"]].isna().all().all()

    X_train, _ = features.split_features_target(features.build_feature_frame(daily))
    preprocessor = features.build_preprocessor().fit(X_train)
    encoded = preprocessor.transform(features.feature_matrix(fresh))
    assert not encoded.isna().any().any()


def test_prediction_with_no_history_still_returns_rows():
    empty = pd.DataFrame(columns=features.DAILY_COLUMNS)
    prediction = features.build_prediction_features(empty, pd.Timestamp("2026-10-13"), LOCATIONS, PRODUCTS)
    assert len(prediction) == 4
    assert (prediction["n_prior_days"] == 0).all()
    assert prediction["day_of_week"].tolist() == [1, 1, 1, 1]  # a Tuesday


# ---------------- splitting ----------------
def test_split_features_target_rejects_unknown_targets():
    daily = synthetic_daily()
    last_day = daily["date"].max()
    prediction = features.build_prediction_features(
        daily[daily["date"] < last_day], last_day, LOCATIONS, PRODUCTS
    )
    with pytest.raises(ValueError, match="known target"):
        features.split_features_target(prediction)


def test_chronological_split_never_mixes_time():
    frame = features.build_feature_frame(synthetic_daily())
    train, test = features.chronological_split(frame, test_days=5)

    assert train["date"].max() < test["date"].min()
    assert test["date"].min() > frame["date"].max() - pd.Timedelta(days=5)
    assert len(train) + len(test) == len(frame)

    with pytest.raises(ValueError):
        features.chronological_split(frame, test_days=100)
    with pytest.raises(ValueError):
        features.chronological_split(frame, test_days=0)


def test_training_rows_can_skip_series_without_history():
    frame = features.build_feature_frame(synthetic_daily())
    everything = features.training_rows(frame)
    with_history = features.training_rows(frame, min_prior_days=1)

    assert len(everything) == len(frame)
    assert len(with_history) < len(everything)
    assert (with_history["n_prior_days"] >= 1).all()


# ---------------- preprocessing ----------------
def test_preprocessor_is_fitted_on_training_rows_only():
    frame = features.build_feature_frame(synthetic_daily())
    train, test = features.chronological_split(frame, test_days=5)
    X_train, _ = features.split_features_target(train)
    X_test, _ = features.split_features_target(test)

    preprocessor = features.build_preprocessor().fit(X_train)

    row = X_test.iloc[[0]].copy()
    row["lag_1"] = np.nan  # a missing value
    row["product_id"] = "brand-new-product"  # an id the model never saw
    encoded = preprocessor.transform(row)

    assert not encoded.isna().any().any()
    assert encoded["lag_1"].iloc[0] == pytest.approx(X_train["lag_1"].median())  # a TRAIN statistic
    product_columns = [c for c in encoded.columns if c.startswith("product_id_")]
    assert product_columns and encoded[product_columns].to_numpy().sum() == 0

    scaled = features.build_preprocessor(scale=True).fit(X_train).transform(X_test)
    assert not scaled.isna().any().any()


def test_every_feature_is_documented():
    assert set(features.FEATURE_DESCRIPTIONS) == set(features.FEATURE_COLUMNS)
    table = features.describe_features()
    assert list(table["feature"]) == features.FEATURE_COLUMNS
    assert set(table["group"]) == {"calendar", "price", "history", "identity"}


# ---------------- cleaning ----------------
def test_clean_daily_rejects_bad_data():
    good = daily_frame([("2026-10-01", 5), ("2026-10-02", 6)])

    with pytest.raises(ValueError, match="one row per"):
        features.clean_daily(pd.concat([good, good.iloc[[0]]], ignore_index=True))
    negative = good.copy()
    negative.loc[0, "units_sold"] = -1.0
    with pytest.raises(ValueError, match="negative"):
        features.clean_daily(negative)
    with pytest.raises(ValueError, match="Missing columns"):
        features.clean_daily(good.drop(columns=["price"]))


def test_clean_daily_fills_missing_prices_and_categories():
    daily = daily_frame([("2026-10-01", 5), ("2026-10-02", 6), ("2026-10-03", 7)], price=110.0)
    daily.loc[1, "price"] = np.nan
    daily.loc[2, "category"] = None

    cleaned = features.clean_daily(daily)
    assert cleaned["price"].tolist() == [110.0, 110.0, 110.0]  # the product's usual price
    assert cleaned.loc[2, "category"] == "unknown"


def test_sessions_are_combined_into_one_day():
    raw = pd.DataFrame(
        [
            ("2026-10-01", "loc-a", "p", "nankhatai", 120.0, 100.0, 10, 0, 10),
            ("2026-10-01", "loc-a", "p", "nankhatai", 120.0, np.nan, 5, 1, 2),
            ("2026-10-02", "loc-a", "q", "nankhatai", 90.0, np.nan, 5, 0, 5),
        ],
        columns=features.RAW_COLUMNS,
    )
    daily = features.aggregate_to_daily(raw).set_index(["product_id"])

    first, second = daily.loc["p"], daily.loc["q"]
    assert (first["stocked_qty"], first["units_sold"], first["wasted_qty"]) == (15, 12, 1)
    assert first["price"] == 100.0  # sessions without sales do not pull the price down
    assert first["was_sold_out"] == 0.0  # 12 of 15
    assert second["price"] == 90.0  # no sales, so today's price
    assert second["was_sold_out"] == 1.0  # 5 of 5


def test_empty_input_gives_empty_outputs_not_errors():
    empty = pd.DataFrame(columns=features.RAW_COLUMNS)
    daily = features.aggregate_to_daily(empty)
    assert daily.empty and list(daily.columns) == features.DAILY_COLUMNS
    assert features.build_feature_frame(daily).empty


# ---------------- the real database path ----------------
def test_database_rows_become_training_and_prediction_features(client, admin_headers, customer_headers):
    today = datetime.now(IST).date()
    location = client.post(
        f"{PREFIX}/stalls/locations",
        json={"name": "Market Gate", "latitude": 12.97, "longitude": 77.59},
        headers=admin_headers,
    ).json()["id"]
    session = client.post(
        f"{PREFIX}/stalls/sessions",
        json={
            "location_id": location,
            "session_date": today.isoformat(),
            "start_time": "09:00:00",
            "end_time": "23:59:00",
        },
        headers=admin_headers,
    ).json()["id"]

    ids = {}
    for name, price in (("Classic Nankhatai", "120.00"), ("Plain Biscuit", "90.00")):
        response = client.post(
            f"{PREFIX}/products", json={"name": name, "price": price}, headers=admin_headers
        )
        ids[name] = response.json()["id"]
        stock = client.put(
            f"{PREFIX}/inventory/sessions/{session}/products/{ids[name]}",
            json={"stocked_qty": 10},
            headers=admin_headers,
        )
        assert stock.status_code == 200, stock.text
    classic, plain = ids["Classic Nankhatai"], ids["Plain Biscuit"]

    def order(quantity):
        response = client.post(
            f"{PREFIX}/orders",
            json={"session_id": session, "items": [{"product_id": classic, "quantity": quantity}]},
            headers=customer_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    order(3)
    cancelled = order(2)
    cancel = client.post(f"{PREFIX}/orders/me/{cancelled}/cancel", headers=customer_headers)
    assert cancel.status_code == 200

    with TestingSession() as db:  # the session is still only "scheduled", so it has not happened
        assert data.build_training_frame(db).empty

    opened = client.patch(
        f"{PREFIX}/stalls/sessions/{session}/status", json={"status": "open"}, headers=admin_headers
    )
    assert opened.status_code == 200
    client.patch(f"{PREFIX}/products/{classic}", json={"price": "200.00"}, headers=admin_headers)

    with TestingSession() as db:
        frame = data.build_training_frame(db)

    assert len(frame) == 2
    rows = frame.set_index("product_id")
    sold, idle = rows.loc[classic], rows.loc[plain]
    assert sold["units_sold"] == 3  # the cancelled order is not demand
    assert sold["stocked_qty"] == 10 and sold["was_sold_out"] == 0
    assert sold["price"] == 120.0  # the price paid, not today's 200
    assert sold["category"] == "nankhatai"
    assert sold["date"] == pd.Timestamp(today)
    assert idle["units_sold"] == 0  # stocked, nothing sold: a real zero
    assert idle["price"] == 90.0  # no sales, so the current price

    X, y = features.split_features_target(features.training_rows(frame))
    assert sorted(y.tolist()) == [0.0, 3.0] and list(X.columns) == features.FEATURE_COLUMNS

    tomorrow = today + timedelta(days=1)
    with TestingSession() as db:
        prediction = data.build_prediction_frame(db, tomorrow)

    assert len(prediction) == 2  # one active location x two active products
    assert prediction[features.TARGET].isna().all()
    forecast_row = prediction.set_index("product_id").loc[classic]
    assert forecast_row["lag_1"] == 3
    assert forecast_row["n_prior_days"] == 1
    assert forecast_row["days_since_last_stocked"] == 1
    assert forecast_row["price"] == 200.0  # tomorrow's price is the current one
    assert forecast_row["day_of_week"] == tomorrow.weekday()
