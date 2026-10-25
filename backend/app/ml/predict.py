"""Demand forecasts from the saved model. Loads and predicts; never trains."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.ml import data, features, train

MAX_HORIZON_DAYS = 7
ID_COLUMNS = ["date", "location_id", "product_id"]

_cache: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any]]] = {}


class ModelUnavailableError(RuntimeError):
    """No usable trained model (missing, stale feature set, unreadable)."""


class InvalidForecastRequest(ValueError):
    """The requested date is not one we can forecast."""


@dataclass(frozen=True)
class ForecastResult:
    model_version: str
    rows: list[dict[str, Any]]


def _load(artifact_dir: Path | str):
    pointer = Path(artifact_dir) / train.LATEST_POINTER
    try:
        key = (str(pointer.resolve()), pointer.stat().st_mtime_ns)
    except FileNotFoundError as exc:
        raise ModelUnavailableError("No trained model found. Run: python -m app.ml.train") from exc
    if key not in _cache:
        try:
            loaded = train.load_model(artifact_dir)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            raise ModelUnavailableError(str(exc)) from exc
        _cache.clear()  # a retrain moves the pointer, so old models are dropped
        _cache[key] = loaded
    return _cache[key]


def _check_date(target_date: date, today: date) -> None:
    if target_date < today:
        raise InvalidForecastRequest("Forecast date cannot be in the past")
    if target_date > today + timedelta(days=MAX_HORIZON_DAYS):
        raise InvalidForecastRequest(f"Forecast date is more than {MAX_HORIZON_DAYS} days ahead")


def forecast_demand(
    db: Session,
    target_date: date,
    location_ids: list[str] | None = None,
    product_ids: list[str] | None = None,
    *,
    artifact_dir: Path | str = train.ARTIFACT_DIR,
    today: date | None = None,
) -> ForecastResult:
    if today is None:
        from app.modules.stalls.service import today_ist

        today = today_ist()
    _check_date(target_date, today)

    bundle, _ = _load(artifact_dir)
    frame = data.build_prediction_frame(db, target_date, location_ids, product_ids)
    if frame.empty:
        return ForecastResult(bundle["version"], [])

    missing = [c for c in ID_COLUMNS if c not in frame.columns]
    if missing:
        raise ModelUnavailableError(f"Prediction frame is missing columns: {missing}")

    predicted = np.clip(bundle["pipeline"].predict(features.feature_matrix(frame)), 0, None)
    rows = [
        {
            "date": pd.Timestamp(d).date(),
            "location_id": str(loc),
            "product_id": str(prod),
            "predicted_units": round(float(units), 2),
        }
        for d, loc, prod, units in zip(
            frame["date"], frame["location_id"], frame["product_id"], predicted
        )
    ]
    return ForecastResult(bundle["version"], rows)