import json

import numpy as np
import pandas as pd
import pytest

from app.ml import features, train
from app.ml.train import InsufficientDataError

BASELINE_NAMES = {"train_mean", "previous_day", "same_weekday_avg", "rolling_7_avg"}


def synthetic_daily(days=70, seed=0):
    """Weekends sell more, loc-a sells more than loc-b, loc-b is not visited every day."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-07-01")
    rows = []
    for offset in range(days):
        day = start + pd.Timedelta(days=offset)
        for location, boost in (("loc-a", 6.0), ("loc-b", 0.0)):
            if location == "loc-b" and offset % 3 == 1:
                continue
            for product, base, price in (("prod-1", 5.0, 120.0), ("prod-2", 2.0, 150.0)):
                lam = base + boost + (8.0 if day.day_of_week >= 5 else 0.0)
                units = float(rng.poisson(lam))
                rows.append(
                    {
                        "date": day,
                        "location_id": location,
                        "product_id": product,
                        "category": "nankhatai",
                        "price": price,
                        "stocked_qty": units + 3.0,
                        "wasted_qty": 0.0,
                        "was_sold_out": 0.0,
                        "units_sold": units,
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def history():
    return features.build_feature_frame(synthetic_daily())


# ---------------- metrics and baselines ----------------
def test_evaluate_metrics_are_correct():
    metrics = train.evaluate([2, 4, 6], [3, 4, 4])
    assert metrics["rows"] == 3
    assert metrics["mean_actual"] == pytest.approx(4.0)
    assert metrics["mae"] == pytest.approx(1.0)
    assert metrics["rmse"] == pytest.approx(1.2910, abs=1e-4)
    assert metrics["wape"] == pytest.approx(0.25)
    assert metrics["bias"] == pytest.approx(-0.3333, abs=1e-4)
    assert train.evaluate([0, 0], [1, 1])["wape"] is None  # no division by zero


def test_baseline_rules_and_fallbacks():
    nan = np.nan
    X_valid = pd.DataFrame(
        {
            "lag_1": [5, nan, nan, nan, nan],
            "same_weekday_mean_4": [3, nan, nan, nan, nan],
            "rolling_mean_7": [8, 8, nan, nan, nan],
            "product_avg_prior": [7, 7, 7, nan, nan],
            "location_avg_prior": [9, 9, 9, 9, nan],
        }
    )
    y_train = pd.Series([2.0, 4.0, 6.0])  # mean 4

    predictions = train.run_baselines(y_train, X_valid)

    assert set(predictions) == BASELINE_NAMES
    np.testing.assert_allclose(predictions["train_mean"], [4, 4, 4, 4, 4])
    np.testing.assert_allclose(predictions["previous_day"], [5, 7, 7, 9, 4])
    np.testing.assert_allclose(predictions["same_weekday_avg"], [3, 8, 7, 9, 4])
    np.testing.assert_allclose(predictions["rolling_7_avg"], [8, 8, 7, 9, 4])


# ---------------- splitting without leakage ----------------
def test_validation_is_later_than_training_and_statistics_come_from_training_only(history, tmp_path):
    known = features.training_rows(history)
    train_rows, valid_rows = train.prepare_data(history, validation_days=14)

    assert train_rows["date"].max() < valid_rows["date"].min()
    assert len(train_rows) + len(valid_rows) == len(known)

    result = train.train_and_save(
        history, artifact_dir=tmp_path, validation_days=14, refit_on_all=False
    )
    imputer = (
        result.pipeline.named_steps["preprocess"]
        .named_transformers_["numeric"]
        .named_steps["impute"]
    )
    index = features.NUMERIC_FEATURES.index("lag_1")
    assert imputer.statistics_[index] == pytest.approx(train_rows["lag_1"].median())


# ---------------- saving ----------------
def test_training_saves_a_model_and_a_full_record(history, tmp_path):
    result = train.train_and_save(history, artifact_dir=tmp_path, validation_days=14)

    assert result.model_path.exists() and result.metadata_path.exists()
    assert result.model_path.parent == tmp_path
    assert list(tmp_path.glob("*.tmp")) == []  # nothing half-written is left behind
    pointer = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert pointer["version"] == result.version
    assert pointer["model_file"] == result.model_path.name

    meta = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert meta == result.metadata  # what is on disk is what was returned

    assert meta["features"]["all"] == features.FEATURE_COLUMNS
    assert features.TARGET not in meta["features"]["all"]
    assert set(meta["features"]["excluded_same_day_columns"]) == set(features.METADATA_COLUMNS)
    assert meta["features"]["encoded_feature_count"] > len(features.NUMERIC_FEATURES)
    assert meta["target"] == features.TARGET
    assert meta["model"]["seed"] == 42
    assert meta["model"]["params"]["loss"] == "poisson"

    split = meta["split"]
    assert split["method"] == "chronological" and split["validation_days"] == 14
    assert split["train_end"] < split["validation_start"]
    assert meta["data"]["rows"] == len(features.training_rows(history))
    assert set(meta["environment"]) == {"python", "scikit_learn", "pandas", "numpy", "joblib"}


def test_the_model_is_compared_with_every_baseline(history, tmp_path):
    validation = train.train_and_save(
        history, artifact_dir=tmp_path, validation_days=14
    ).metadata["validation"]

    assert set(validation["baselines"]) == BASELINE_NAMES
    assert validation["best_baseline"] in BASELINE_NAMES
    best_mae = min(m["mae"] for m in validation["baselines"].values())
    assert validation["baselines"][validation["best_baseline"]]["mae"] == best_mae

    model_mae = validation["model"]["mae"]
    assert validation["beats_baseline"] == (model_mae < best_mae)  # the verdict is consistent
    # The signal (weekends and location) is strong, so the model must clearly beat the plain mean.
    assert model_mae < validation["baselines"]["train_mean"]["mae"]


def test_a_saved_model_loads_and_predicts(history, tmp_path):
    result = train.train_and_save(history, artifact_dir=tmp_path, validation_days=14)

    bundle, meta = train.load_model(tmp_path)
    X, _ = features.split_features_target(features.training_rows(history))
    predictions = bundle["pipeline"].predict(X)

    np.testing.assert_allclose(predictions, result.pipeline.predict(X))
    assert np.isfinite(predictions).all() and (predictions >= 0).all()
    assert bundle["feature_columns"] == features.FEATURE_COLUMNS
    assert meta["version"] == result.version
    assert train.load_model(tmp_path, version=result.version)[1] == meta


def test_a_newer_training_run_becomes_the_latest(history, tmp_path):
    first = train.train_and_save(history, artifact_dir=tmp_path, validation_days=14)
    second = train.train_and_save(history, artifact_dir=tmp_path, validation_days=14)

    assert first.version != second.version
    assert first.model_path.exists() and second.model_path.exists()  # old versions are kept
    assert train.load_model(tmp_path)[1]["version"] == second.version


# ---------------- reproducibility ----------------
def test_training_is_reproducible(history, tmp_path):
    first = train.train_and_save(history, artifact_dir=tmp_path / "a", validation_days=14)
    second = train.train_and_save(history, artifact_dir=tmp_path / "b", validation_days=14)

    assert first.metadata["data"]["fingerprint"] == second.metadata["data"]["fingerprint"]
    assert first.metadata["validation"] == second.metadata["validation"]
    X, _ = features.split_features_target(features.training_rows(history))
    np.testing.assert_allclose(first.pipeline.predict(X), second.pipeline.predict(X))

    changed = history.copy()
    changed.loc[changed.index[0], "units_sold"] += 1
    assert train.data_fingerprint(changed) != train.data_fingerprint(history)


def test_refitting_on_all_rows_does_not_change_the_reported_validation(history, tmp_path):
    full = train.train_and_save(
        history, artifact_dir=tmp_path / "full", validation_days=14, refit_on_all=True
    )
    held = train.train_and_save(
        history, artifact_dir=tmp_path / "held", validation_days=14, refit_on_all=False
    )

    assert full.metadata["refit_on_all"] is True and held.metadata["refit_on_all"] is False
    assert full.metadata["trained_on"]["rows"] == len(features.training_rows(history))
    assert held.metadata["trained_on"]["rows"] == held.metadata["split"]["train_rows"]
    assert full.metadata["validation"] == held.metadata["validation"]


# ---------------- refusing bad situations ----------------
def test_training_refuses_when_there_is_not_enough_data(history, tmp_path):
    empty = features.build_feature_frame(pd.DataFrame(columns=features.DAILY_COLUMNS))
    with pytest.raises(InsufficientDataError):
        train.train_and_save(empty, artifact_dir=tmp_path)

    tiny = features.build_feature_frame(synthetic_daily(days=6))
    with pytest.raises(InsufficientDataError):
        train.train_and_save(tiny, artifact_dir=tmp_path)

    with pytest.raises(InsufficientDataError, match="training rows"):
        train.train_and_save(history, artifact_dir=tmp_path, validation_days=14, min_train_rows=10000)
    with pytest.raises(InsufficientDataError, match="validation rows"):
        train.train_and_save(history, artifact_dir=tmp_path, validation_days=14, min_validation_rows=10000)

    assert list(tmp_path.iterdir()) == []  # a refused run writes nothing


def test_training_refuses_when_nothing_was_ever_sold(tmp_path):
    daily = synthetic_daily()
    daily["units_sold"] = 0.0
    silent = features.build_feature_frame(daily)

    with pytest.raises(InsufficientDataError, match="No units"):
        train.train_and_save(silent, artifact_dir=tmp_path, validation_days=14)
    assert list(tmp_path.iterdir()) == []


def test_invalid_settings_are_rejected(history, tmp_path):
    with pytest.raises(ValueError):
        train.train_and_save(history, artifact_dir=tmp_path, validation_days=0)


def test_loading_problems_are_reported_clearly(history, tmp_path, monkeypatch):
    with pytest.raises(FileNotFoundError, match="No trained model"):
        train.load_model(tmp_path)

    train.train_and_save(history, artifact_dir=tmp_path, validation_days=14)

    with pytest.raises(ValueError, match="Invalid model version"):
        train.load_model(tmp_path, version="../../secrets")
    with pytest.raises(FileNotFoundError):
        train.load_model(tmp_path, version="20200101T000000000Z")

    monkeypatch.setattr(features, "FEATURE_COLUMNS", list(reversed(features.FEATURE_COLUMNS)))
    with pytest.raises(ValueError, match="different feature set"):
        train.load_model(tmp_path)
