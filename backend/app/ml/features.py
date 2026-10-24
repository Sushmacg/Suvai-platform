"""Feature engineering for Suvai demand prediction.

Pure pandas / NumPy / scikit-learn. Nothing here touches the database or FastAPI,
so the same functions serve training, evaluation and live prediction.

The unit of prediction
    One row = one (date, location, product): "how many units of this product will be
    demanded at this location on this day?"

The target
    units_sold = units reserved by orders that were not cancelled, summed over the
    stall sessions held that day (it equals session_stock.sold_qty).

The rule that prevents data leakage
    A row's features may only use information from EARLIER dates. Anything that
    describes the row's own day (units sold, stock, waste, sold-out flag) is kept
    as metadata and is never a feature.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ----------------------------------------------------------------- names
TARGET = "units_sold"
SERIES_KEYS = ["location_id", "product_id"]  # one series per location and product
ROW_KEYS = ["date", "location_id", "product_id"]

# What data.py gives us: one row per stocked product per session.
RAW_COLUMNS = [
    "date",
    "location_id",
    "product_id",
    "category",
    "current_price",
    "avg_price",
    "stocked_qty",
    "wasted_qty",
    "units_sold",
]

# The daily table: one row per date, location and product.
DAILY_COLUMNS = [
    "date",
    "location_id",
    "product_id",
    "category",
    "price",
    "stocked_qty",
    "wasted_qty",
    "was_sold_out",
    TARGET,
]

# Facts about the day itself. Useful for analysis, forbidden as features.
METADATA_COLUMNS = ["stocked_qty", "wasted_qty", "was_sold_out"]

CALENDAR_FEATURES = [
    "day_of_week",
    "is_weekend",
    "month",
    "day_of_month",
    "week_of_year",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
]
HISTORY_FEATURES = [
    "lag_1",
    "lag_2",
    "rolling_mean_3",
    "rolling_mean_7",
    "rolling_std_7",
    "expanding_mean",
    "same_weekday_lag_1",
    "same_weekday_mean_4",
    "prior_sold_out_rate_7",
    "n_prior_days",
    "days_since_last_stocked",
    "product_avg_prior",
    "location_avg_prior",
]
NUMERIC_FEATURES = CALENDAR_FEATURES + ["price"] + HISTORY_FEATURES
CATEGORICAL_FEATURES = ["location_id", "product_id", "category"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

_ALL_COLUMNS = DAILY_COLUMNS + CALENDAR_FEATURES + HISTORY_FEATURES

if {TARGET, *METADATA_COLUMNS} & set(FEATURE_COLUMNS):
    raise RuntimeError("The target or a same-day column was added to FEATURE_COLUMNS")

FEATURE_DESCRIPTIONS = {
    "day_of_week": "0=Monday ... 6=Sunday. Footfall differs between weekdays and weekends.",
    "is_weekend": "1 on Saturday and Sunday. Markets and offices behave differently.",
    "month": "Seasonality, such as festival months and cooler months.",
    "day_of_month": "Spending often follows the salary cycle.",
    "week_of_year": "Finer seasonality than month (ISO week number).",
    "dow_sin": "Cyclic encoding of the weekday, so Sunday sits next to Monday.",
    "dow_cos": "Second half of the cyclic weekday encoding.",
    "month_sin": "Cyclic encoding of the month, so December sits next to January.",
    "month_cos": "Second half of the cyclic month encoding.",
    "price": "Price that day (order-line price if it sold, else the current price).",
    "lag_1": "Demand on the previous day this product was stocked here. Strongest single signal.",
    "lag_2": "Demand two stocked days ago. Shows the direction of the trend.",
    "rolling_mean_3": "Average of the last 3 stocked days. Smoothed recent level.",
    "rolling_mean_7": "Average of the last 7 stocked days. About one week of context.",
    "rolling_std_7": "Spread of the last 7 stocked days. Separates steady from spiky sellers.",
    "expanding_mean": "Average of all earlier days for this location and product.",
    "same_weekday_lag_1": "Demand on the previous same weekday here. Captures the weekly pattern.",
    "same_weekday_mean_4": "Average of the last 4 same weekdays here.",
    "prior_sold_out_rate_7": "Share of the last 7 stocked days that sold out. Sales understate demand then.",
    "n_prior_days": "How many earlier days of history exist. Tells the model how far to trust the lags.",
    "days_since_last_stocked": "Days since this product was last stocked here. Visits are irregular.",
    "product_avg_prior": "Average demand for this product at all locations on earlier dates.",
    "location_avg_prior": "Average demand for all products at this location on earlier dates.",
    "location_id": "Which location. Some spots are simply busier.",
    "product_id": "Which product. Some products simply sell more.",
    "category": "Product group. Helps when a product has little history of its own.",
}


def describe_features() -> pd.DataFrame:
    """A readable table of every feature: its group and why it helps."""
    groups = {name: "calendar" for name in CALENDAR_FEATURES}
    groups["price"] = "price"
    groups.update({name: "history" for name in HISTORY_FEATURES})
    groups.update({name: "identity" for name in CATEGORICAL_FEATURES})
    return pd.DataFrame(
        [
            {"feature": name, "group": groups[name], "why_it_helps": FEATURE_DESCRIPTIONS[name]}
            for name in FEATURE_COLUMNS
        ]
    )


# ------------------------------------------------------- cleaning and shaping
def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def aggregate_to_daily(raw: pd.DataFrame) -> pd.DataFrame:
    """Session-level rows -> one row per (date, location, product)."""
    _require_columns(raw, RAW_COLUMNS)
    if raw.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    df = raw[RAW_COLUMNS].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["location_id"] = df["location_id"].astype(str)
    df["product_id"] = df["product_id"].astype(str)

    daily = df.groupby(ROW_KEYS, as_index=False).agg(
        category=("category", "first"),
        current_price=("current_price", "first"),
        avg_price=("avg_price", "mean"),  # NaN-safe: sessions without sales are skipped
        stocked_qty=("stocked_qty", "sum"),
        wasted_qty=("wasted_qty", "sum"),
        units_sold=("units_sold", "sum"),
    )
    # Price at the time of the orders if there were any, otherwise today's price.
    daily["price"] = daily["avg_price"].fillna(daily["current_price"])
    daily["was_sold_out"] = (
        (daily["stocked_qty"] > 0) & (daily["units_sold"] >= daily["stocked_qty"])
    ).astype(float)
    return daily[DAILY_COLUMNS]


def clean_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise a daily table. Rows with an unknown target (the
    future) are allowed; their target is NaN."""
    _require_columns(daily, DAILY_COLUMNS)
    df = daily[DAILY_COLUMNS].copy()
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    for column in ("location_id", "product_id"):
        df[column] = df[column].astype(str)
    df["category"] = df["category"].fillna("unknown").astype(str)
    for column in ("price", "stocked_qty", "wasted_qty", "was_sold_out", TARGET):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)

    if (df[TARGET] < 0).any():
        raise ValueError("units_sold cannot be negative")
    if df.duplicated(ROW_KEYS).any():
        raise ValueError("Expected one row per date, location and product")

    # Missing price: the product's usual price, then the overall median, then 0.
    usual = df.groupby("product_id")["price"].transform("median")
    df["price"] = df["price"].fillna(usual).fillna(df["price"].median()).fillna(0.0)
    return df


# -------------------------------------------------------------- calendar
def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features known in advance for any date, so they can never leak."""
    out = df.copy()
    dates = pd.to_datetime(out["date"])
    weekday = dates.dt.day_of_week
    month = dates.dt.month

    out["day_of_week"] = weekday.astype(int)
    out["is_weekend"] = (weekday >= 5).astype(int)
    out["month"] = month.astype(int)
    out["day_of_month"] = dates.dt.day.astype(int)
    out["week_of_year"] = dates.dt.isocalendar().week.astype(int)
    out["dow_sin"] = np.sin(2 * np.pi * weekday / 7)
    out["dow_cos"] = np.cos(2 * np.pi * weekday / 7)
    out["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12)
    out["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12)
    return out


# --------------------------------------------------------------- history
def _prior_mean_by_date(df: pd.DataFrame, group_col: str, target: str) -> np.ndarray:
    """Mean of the target over ALL rows of the group on EARLIER dates.

    Done per date (not per row) so rows from the same date, for example another
    location on the same day, are never included.
    """
    observed = df[target].notna()
    work = pd.DataFrame(
        {
            group_col: df[group_col],
            "date": df["date"],
            "_total": df[target].where(observed, 0.0),
            "_count": observed.astype(float),
        }
    )
    daily = work.groupby([group_col, "date"], as_index=False)[["_total", "_count"]].sum()
    daily = daily.sort_values([group_col, "date"]).reset_index(drop=True)

    grouped = daily.groupby(group_col, sort=False)
    prior_total = grouped["_total"].cumsum() - daily["_total"]  # up to the previous date
    prior_count = grouped["_count"].cumsum() - daily["_count"]
    daily["prior_mean"] = prior_total / prior_count.where(prior_count > 0)

    merged = df[[group_col, "date"]].merge(
        daily[[group_col, "date", "prior_mean"]], on=[group_col, "date"], how="left"
    )
    return merged["prior_mean"].to_numpy()


def add_history_features(df: pd.DataFrame, target: str = TARGET) -> pd.DataFrame:
    """Features built from EARLIER rows only.

    Every window is applied to the target shifted by one row, so a row never sees
    its own value or anything after it. Rows with a NaN target (the future) take
    part as rows, but contribute nothing to any average.
    """
    base = df.sort_values(SERIES_KEYS + ["date"], kind="mergesort").reset_index(drop=True)
    base = base.assign(_weekday=base["date"].dt.day_of_week)
    by_series = base.groupby(SERIES_KEYS, sort=False)
    by_weekday = base.groupby(SERIES_KEYS + ["_weekday"], sort=False)

    def earlier(grouped, column, summary):
        return grouped[column].transform(lambda s: summary(s.shift(1)))

    observed = base[target].notna().astype(int)
    new = pd.DataFrame(
        {
            "lag_1": by_series[target].shift(1),
            "lag_2": by_series[target].shift(2),
            "rolling_mean_3": earlier(
                by_series, target, lambda s: s.rolling(3, min_periods=1).mean()
            ),
            "rolling_mean_7": earlier(
                by_series, target, lambda s: s.rolling(7, min_periods=1).mean()
            ),
            "rolling_std_7": earlier(
                by_series, target, lambda s: s.rolling(7, min_periods=2).std()
            ),
            "expanding_mean": earlier(by_series, target, lambda s: s.expanding().mean()),
            "same_weekday_lag_1": by_weekday[target].shift(1),
            "same_weekday_mean_4": earlier(
                by_weekday, target, lambda s: s.rolling(4, min_periods=1).mean()
            ),
            "prior_sold_out_rate_7": earlier(
                by_series, "was_sold_out", lambda s: s.rolling(7, min_periods=1).mean()
            ),
            "n_prior_days": observed.groupby(
                [base["location_id"], base["product_id"]]
            ).cumsum()
            - observed,
            "days_since_last_stocked": (base["date"] - by_series["date"].shift(1)).dt.days,
            "product_avg_prior": pd.Series(
                _prior_mean_by_date(base, "product_id", target), index=base.index
            ),
            "location_avg_prior": pd.Series(
                _prior_mean_by_date(base, "location_id", target), index=base.index
            ),
        },
        index=base.index,
    )
    return pd.concat([base.drop(columns="_weekday"), new], axis=1)


def build_feature_frame(daily: pd.DataFrame) -> pd.DataFrame:
    """The one entry point: daily table -> calendar and history features.

    Used unchanged for training and for prediction. Rows whose target is NaN are
    future rows: they get features but no target."""
    df = clean_daily(daily)
    if df.empty:
        return pd.DataFrame(columns=_ALL_COLUMNS)
    df = add_calendar_features(df)
    df = add_history_features(df)
    return df.sort_values(["date"] + SERIES_KEYS, kind="mergesort").reset_index(drop=True)


# ------------------------------------------------------------ prediction
def make_future_rows(
    target_date: date, location_ids: list[str], products: pd.DataFrame
) -> pd.DataFrame:
    """One row per location and product for a day that has not happened yet."""
    locations = pd.DataFrame({"location_id": [str(x) for x in location_ids]})
    catalog = products[["product_id", "category", "price"]].copy()
    catalog["product_id"] = catalog["product_id"].astype(str)

    rows = locations.merge(catalog, how="cross")
    rows["date"] = pd.Timestamp(target_date).normalize()
    for column in ["stocked_qty", "wasted_qty", "was_sold_out", TARGET]:
        rows[column] = np.nan
    return rows[DAILY_COLUMNS]


def build_prediction_features(
    history_daily: pd.DataFrame,
    target_date: date,
    location_ids: list[str],
    products: pd.DataFrame,
) -> pd.DataFrame:
    """Features for every location and product on target_date.

    History is cut at date < target_date, so only what would really be known on
    that morning is used. The same build_feature_frame code runs as in training,
    so training and prediction cannot drift apart."""
    target = pd.Timestamp(target_date).normalize()

    history = clean_daily(history_daily)
    if not history.empty:
        history = history[history["date"] < target]
    future = clean_daily(make_future_rows(target, location_ids, products))

    parts = [part for part in (history, future) if not part.empty]
    if not parts:
        return pd.DataFrame(columns=_ALL_COLUMNS)

    frame = build_feature_frame(pd.concat(parts, ignore_index=True))
    return frame[frame["date"] == target].reset_index(drop=True)


# ------------------------------------------------ features, target, splitting
def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Only the feature columns, in a fixed order."""
    _require_columns(frame, FEATURE_COLUMNS)
    X = frame[FEATURE_COLUMNS].copy()
    for column in CATEGORICAL_FEATURES:
        X[column] = X[column].astype(object)
    return X


def split_features_target(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """X (features) and y (target) for training or evaluation."""
    _require_columns(frame, [TARGET])
    if frame[TARGET].isna().any():
        raise ValueError("Rows without a known target cannot be used for training or evaluation")
    return feature_matrix(frame), frame[TARGET].astype(float)


def training_rows(frame: pd.DataFrame, min_prior_days: int = 0) -> pd.DataFrame:
    """Rows with a known target. min_prior_days=1 drops each series' very first day,
    which has no history at all."""
    rows = frame[frame[TARGET].notna()]
    return rows[rows["n_prior_days"] >= min_prior_days].copy()


def chronological_split(
    frame: pd.DataFrame, test_days: int = 28
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The last test_days calendar days become the test set. Never shuffle time series:
    a random split would let the model learn from the future."""
    if test_days < 1:
        raise ValueError("test_days must be at least 1")
    if frame.empty:
        raise ValueError("There are no rows to split")

    cutoff = frame["date"].max() - pd.Timedelta(days=test_days)
    train = frame[frame["date"] <= cutoff]
    test = frame[frame["date"] > cutoff]
    if train.empty or test.empty:
        raise ValueError("Not enough history for this split. Reduce test_days or add more data")
    return train.copy(), test.copy()


def build_preprocessor(scale: bool = False) -> ColumnTransformer:
    """Imputes missing values and one-hot encodes the identity columns.

    Fit it on TRAINING rows only (preprocessor.fit(X_train)), then use .transform on
    test rows and on live rows. Fitting on all data would leak test statistics.
    Tree models do not need scale=True; linear models do."""
    numeric_steps = [("impute", SimpleImputer(strategy="median", keep_empty_features=True))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", Pipeline(numeric_steps), NUMERIC_FEATURES),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="constant", fill_value="unknown")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    preprocessor.set_output(transform="pandas")
    return preprocessor
