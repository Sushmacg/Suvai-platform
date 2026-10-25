"""Model training for Suvai demand prediction.

Run from the backend folder:

    python -m app.ml.train

What it does
    1. Builds the training table from the database (features.py does the feature work).
    2. Splits it by TIME: the last N days become the validation period.
    3. Scores simple baselines first. The model has to beat them to be worth using.
    4. Trains a gradient-boosting model with a Poisson loss (units sold are counts).
    5. Saves the model and a JSON record of exactly how it was built to
       app/ml/artifacts/ (git-ignored).

Nothing here is served by the API yet. Prediction comes later.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline

from app.ml import features

# Resolved from this file's location, so it is always backend/app/ml/artifacts,
# whichever folder the command is run from.
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

DEFAULT_SEED = 42
DEFAULT_VALIDATION_DAYS = 28
MIN_TRAIN_ROWS = 50
MIN_VALIDATION_ROWS = 10
SCHEMA_VERSION = 1
MODEL_FILE_PREFIX = "demand_model"
LATEST_POINTER = "latest.json"
_VERSION_PATTERN = re.compile(r"^\d{8}T\d{9}Z$")

# No early stopping and no subsampling, so the result does not depend on hidden randomness.
MODEL_PARAMS: dict[str, Any] = {
    "loss": "poisson",
    "learning_rate": 0.05,
    "max_iter": 300,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 10,
    "l2_regularization": 1.0,
    "early_stopping": False,
}

# Each baseline uses the first column that has a value, then the next, and so on.
BASELINE_CHAINS: dict[str, list[str]] = {
    "previous_day": ["lag_1", "product_avg_prior", "location_avg_prior"],
    "same_weekday_avg": [
        "same_weekday_mean_4",
        "rolling_mean_7",
        "product_avg_prior",
        "location_avg_prior",
    ],
    "rolling_7_avg": ["rolling_mean_7", "product_avg_prior", "location_avg_prior"],
}

TARGET_NOTE = (
    "units_sold is capped by stock. On days a product sold out, true demand was higher "
    "than the recorded value, so the model learns sales rather than unconstrained demand."
)


class InsufficientDataError(ValueError):
    """There is not enough history to train a meaningful model."""


@dataclass
class TrainingResult:
    version: str
    model_path: Path
    metadata_path: Path
    metadata: dict[str, Any]
    pipeline: Pipeline


# ------------------------------------------------------------------ metrics
def _round(value: float) -> float:
    return round(float(value), 4)


def evaluate(y_true, y_pred) -> dict[str, Any]:
    """MAE and RMSE in units, WAPE as a share of total sales, bias = mean(pred - actual)."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    errors = predicted - actual
    total = float(actual.sum())
    return {
        "rows": int(len(actual)),
        "mean_actual": _round(actual.mean()),
        "mae": _round(np.abs(errors).mean()),
        "rmse": _round(np.sqrt((errors**2).mean())),
        "wape": _round(np.abs(errors).sum() / total) if total > 0 else None,
        "bias": _round(errors.mean()),
    }


# ---------------------------------------------------------------- baselines
def _fallback_chain(X: pd.DataFrame, columns: list[str], default: float) -> np.ndarray:
    prediction = pd.Series(np.nan, index=X.index)
    for column in columns:
        prediction = prediction.fillna(X[column])
    return prediction.fillna(default).to_numpy(dtype=float)


def run_baselines(y_train: pd.Series, X_valid: pd.DataFrame) -> dict[str, np.ndarray]:
    """Simple rules the real model has to beat. Only training statistics are used."""
    train_mean = float(y_train.mean())
    predictions = {
        "train_mean": DummyRegressor(strategy="mean")
        .fit(np.zeros((len(y_train), 1)), y_train)
        .predict(np.zeros((len(X_valid), 1)))
    }
    for name, columns in BASELINE_CHAINS.items():
        predictions[name] = _fallback_chain(X_valid, columns, train_mean)
    return predictions


# -------------------------------------------------------------------- model
def make_model(seed: int = DEFAULT_SEED) -> Pipeline:
    """Preprocessing and model in one pipeline, so fitting it on training rows fits both."""
    return Pipeline(
        [
            ("preprocess", features.build_preprocessor(scale=False)),
            ("model", HistGradientBoostingRegressor(random_state=seed, **MODEL_PARAMS)),
        ]
    )


# --------------------------------------------------------------------- data
def prepare_data(
    frame: pd.DataFrame,
    validation_days: int = DEFAULT_VALIDATION_DAYS,
    min_train_rows: int = MIN_TRAIN_ROWS,
    min_validation_rows: int = MIN_VALIDATION_ROWS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Known-target rows, split by time into (train, validation)."""
    if validation_days < 1:
        raise ValueError("validation_days must be at least 1")

    known = features.training_rows(frame)
    if known.empty:
        raise InsufficientDataError(
            "There are no past sales to learn from yet. Stock needs to be set for sessions "
            "that were opened or closed."
        )
    try:
        train_rows, valid_rows = features.chronological_split(known, test_days=validation_days)
    except ValueError as error:
        raise InsufficientDataError(
            f"Not enough history for a {validation_days}-day validation period. "
            "Add more history or use a shorter --validation-days."
        ) from error

    if len(train_rows) < min_train_rows:
        raise InsufficientDataError(
            f"Only {len(train_rows)} training rows (at least {min_train_rows} needed)."
        )
    if len(valid_rows) < min_validation_rows:
        raise InsufficientDataError(
            f"Only {len(valid_rows)} validation rows (at least {min_validation_rows} needed)."
        )
    if float(train_rows[features.TARGET].sum()) <= 0:
        raise InsufficientDataError(
            "No units were sold in the training period, so there is nothing to learn from."
        )
    return train_rows, valid_rows


def data_fingerprint(frame: pd.DataFrame) -> str:
    """A hash of the training data. Equal data gives an equal fingerprint."""
    columns = list(dict.fromkeys(["date", *features.FEATURE_COLUMNS, features.TARGET]))
    ordered = frame.sort_values(["date", *features.SERIES_KEYS], kind="mergesort")[columns]
    hashes = pd.util.hash_pandas_object(ordered, index=False)
    return hashlib.sha256(hashes.to_numpy().tobytes()).hexdigest()


def _period(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "start": frame["date"].min().date().isoformat(),
        "end": frame["date"].max().date().isoformat(),
    }


def _environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "joblib": joblib.__version__,
    }


# ----------------------------------------------------------------- training
def train_and_save(
    frame: pd.DataFrame,
    *,
    artifact_dir: Path | str = ARTIFACT_DIR,
    validation_days: int = DEFAULT_VALIDATION_DAYS,
    seed: int = DEFAULT_SEED,
    refit_on_all: bool = True,
    min_train_rows: int = MIN_TRAIN_ROWS,
    min_validation_rows: int = MIN_VALIDATION_ROWS,
) -> TrainingResult:
    """Validate against baselines, fit the model, and save it with a full record."""
    train_rows, valid_rows = prepare_data(
        frame, validation_days, min_train_rows, min_validation_rows
    )
    known = features.training_rows(frame)
    X_train, y_train = features.split_features_target(train_rows)
    X_valid, y_valid = features.split_features_target(valid_rows)

    # 1. Baselines first.
    baseline_metrics = {
        name: evaluate(y_valid, prediction)
        for name, prediction in run_baselines(y_train, X_valid).items()
    }
    best_baseline = min(baseline_metrics, key=lambda name: (baseline_metrics[name]["mae"], name))

    # 2. The model, fitted on the training period only and scored on the validation period.
    held_out = make_model(seed).fit(X_train, y_train)
    model_metrics = evaluate(y_valid, np.clip(held_out.predict(X_valid), 0, None))

    baseline_mae = baseline_metrics[best_baseline]["mae"]
    beats_baseline = model_metrics["mae"] < baseline_mae
    improvement = (
        round((baseline_mae - model_metrics["mae"]) / baseline_mae * 100, 2)
        if baseline_mae > 0
        else None
    )

    # 3. The model that gets saved.
    if refit_on_all:
        X_all, y_all = features.split_features_target(known)
        final_model = make_model(seed).fit(X_all, y_all)
        final_rows = known
    else:
        final_model, final_rows = held_out, train_rows

    created = datetime.now(timezone.utc)
    version = created.strftime("%Y%m%dT%H%M%S") + f"{created.microsecond // 1000:03d}Z"
    model_file = f"{MODEL_FILE_PREFIX}_{version}.joblib"
    metadata_file = f"{MODEL_FILE_PREFIX}_{version}.json"

    metadata: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "created_at": created.isoformat(),
        "model": {
            "algorithm": "HistGradientBoostingRegressor",
            "params": {**MODEL_PARAMS, "random_state": seed},
            "seed": seed,
            "pipeline_steps": [
                "preprocess: median imputation + one-hot encoding, fitted on training rows",
                "model: gradient boosting with Poisson loss",
            ],
        },
        "target": features.TARGET,
        "target_note": TARGET_NOTE,
        "features": {
            "all": list(features.FEATURE_COLUMNS),
            "numeric": list(features.NUMERIC_FEATURES),
            "categorical": list(features.CATEGORICAL_FEATURES),
            "encoded_feature_count": int(
                len(final_model.named_steps["preprocess"].get_feature_names_out())
            ),
            "excluded_same_day_columns": list(features.METADATA_COLUMNS),
        },
        "data": {
            "fingerprint": data_fingerprint(known),
            "rows": int(len(known)),
            "date_min": known["date"].min().date().isoformat(),
            "date_max": known["date"].max().date().isoformat(),
            "series_count": int(known.groupby(features.SERIES_KEYS).ngroups),
            "sold_out_rows": int(known["was_sold_out"].sum()),
        },
        "split": {
            "method": "chronological",
            "validation_days": int(validation_days),
            "train_rows": int(len(train_rows)),
            "train_start": train_rows["date"].min().date().isoformat(),
            "train_end": train_rows["date"].max().date().isoformat(),
            "validation_rows": int(len(valid_rows)),
            "validation_start": valid_rows["date"].min().date().isoformat(),
            "validation_end": valid_rows["date"].max().date().isoformat(),
        },
        "refit_on_all": bool(refit_on_all),
        "trained_on": _period(final_rows),
        "validation": {
            "model": model_metrics,
            "baselines": baseline_metrics,
            "best_baseline": best_baseline,
            "beats_baseline": bool(beats_baseline),
            "mae_improvement_pct": improvement,
        },
        "environment": _environment(),
        "files": {"model": model_file, "metadata": metadata_file},
    }

    bundle = {
        "pipeline": final_model,
        "feature_columns": list(features.FEATURE_COLUMNS),
        "target": features.TARGET,
        "version": version,
    }
    model_path, metadata_path = _save(Path(artifact_dir), version, bundle, metadata)
    return TrainingResult(
        version=version,
        model_path=model_path,
        metadata_path=metadata_path,
        metadata=metadata,
        pipeline=final_model,
    )


# ------------------------------------------------------------------- saving
def _save(
    artifact_dir: Path, version: str, bundle: dict[str, Any], metadata: dict[str, Any]
) -> tuple[Path, Path]:
    """Writes the model, then its record, and only then updates 'latest', so a
    half-finished run can never leave 'latest' pointing at missing files."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / metadata["files"]["model"]
    metadata_path = artifact_dir / metadata["files"]["metadata"]

    model_tmp = artifact_dir / (model_path.name + ".tmp")
    joblib.dump(bundle, model_tmp)
    os.replace(model_tmp, model_path)

    _write_json(metadata_path, metadata)
    _write_json(
        artifact_dir / LATEST_POINTER,
        {
            "version": version,
            "model_file": model_path.name,
            "metadata_file": metadata_path.name,
        },
    )
    return model_path, metadata_path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_model(
    artifact_dir: Path | str = ARTIFACT_DIR, version: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a saved model (latest by default) with its metadata.

    Only load files this project created: joblib files can run code when loaded."""
    artifact_dir = Path(artifact_dir)
    if version is None:
        pointer = artifact_dir / LATEST_POINTER
        if not pointer.exists():
            raise FileNotFoundError("No trained model found. Run: python -m app.ml.train")
        version = json.loads(pointer.read_text(encoding="utf-8"))["version"]
    if not _VERSION_PATTERN.match(version):
        raise ValueError(f"Invalid model version: {version!r}")

    model_path = artifact_dir / f"{MODEL_FILE_PREFIX}_{version}.joblib"
    metadata_path = artifact_dir / f"{MODEL_FILE_PREFIX}_{version}.json"
    if not model_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"Model version {version} was not found in {artifact_dir}")

    bundle = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if bundle["feature_columns"] != features.FEATURE_COLUMNS:
        raise ValueError(
            "The saved model was trained with a different feature set. "
            "Retrain with: python -m app.ml.train"
        )
    trained_with = metadata["environment"]["scikit_learn"]
    if trained_with != sklearn.__version__:
        warnings.warn(
            f"This model was trained with scikit-learn {trained_with} but "
            f"{sklearn.__version__} is installed. Retrain if predictions look wrong.",
            stacklevel=2,
        )
    return bundle, metadata


# ---------------------------------------------------------------------- CLI
def format_report(result: TrainingResult) -> str:
    meta = result.metadata
    split = meta["split"]
    validation = meta["validation"]

    def cell(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.3f}"

    ordered = sorted(validation["baselines"], key=lambda n: validation["baselines"][n]["mae"])
    rows = [("MODEL", validation["model"])] + [(n, validation["baselines"][n]) for n in ordered]

    lines = [
        f"Training period:   {split['train_start']} to {split['train_end']} "
        f"({split['train_rows']} rows)",
        f"Validation period: {split['validation_start']} to {split['validation_end']} "
        f"({split['validation_rows']} rows)",
        "",
        f"{'':<20}{'MAE':>9}{'RMSE':>9}{'WAPE':>9}{'Bias':>9}",
    ]
    for name, metrics in rows:
        lines.append(
            f"{name:<20}{cell(metrics['mae']):>9}{cell(metrics['rmse']):>9}"
            f"{cell(metrics['wape']):>9}{cell(metrics['bias']):>9}"
        )
    lines.append("")
    if validation["beats_baseline"]:
        gain = validation["mae_improvement_pct"]
        lines.append(
            f"The model beats the best baseline ({validation['best_baseline']})"
            + (f" by {gain}% on MAE." if gain is not None else ".")
        )
    else:
        lines.append(
            f"WARNING: the model did NOT beat the best baseline ({validation['best_baseline']}). "
            "A simple rule is as good or better with this much data."
        )
    lines += [
        "",
        f"Saved version {result.version}"
        + (" (refitted on all rows)" if meta["refit_on_all"] else " (training period only)"),
        f"  model:    {result.model_path}",
        f"  metadata: {result.metadata_path}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the Suvai demand model.")
    parser.add_argument("--validation-days", type=int, default=DEFAULT_VALIDATION_DAYS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--no-refit",
        action="store_true",
        help="save the model trained on the training period only",
    )
    parser.add_argument("--min-train-rows", type=int, default=MIN_TRAIN_ROWS)
    parser.add_argument("--min-validation-rows", type=int, default=MIN_VALIDATION_ROWS)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    args = parser.parse_args(argv)
    if args.validation_days < 1:
        parser.error("--validation-days must be at least 1")

    from app.db.session import SessionLocal
    from app.ml import data

    with SessionLocal() as db:
        frame = data.build_training_frame(db)

    try:
        result = train_and_save(
            frame,
            artifact_dir=args.artifact_dir,
            validation_days=args.validation_days,
            seed=args.seed,
            refit_on_all=not args.no_refit,
            min_train_rows=args.min_train_rows,
            min_validation_rows=args.min_validation_rows,
        )
    except InsufficientDataError as error:
        print(f"Cannot train yet: {error}")
        print("A model needs weeks of real or generated sales history.")
        return 1

    print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
