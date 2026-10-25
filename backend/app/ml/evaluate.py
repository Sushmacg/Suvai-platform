"""Score the saved model on rows it never trained on, and show where it is weak."""
import argparse

import pandas as pd

from app.ml import data, features, train


def evaluate_saved_model(frame: pd.DataFrame, artifact_dir=train.ARTIFACT_DIR, version=None) -> dict:
    """Rows after the model's last training date. Empty if the model was refit on all rows."""
    bundle, meta = train.load_model(artifact_dir, version)
    cutoff = meta["data"]["date_max"] if meta["refit_on_all"] else meta["split"]["train_end"]
    known = features.training_rows(frame)
    rows = known[known["date"] > pd.Timestamp(cutoff)].copy()
    result = {"version": meta["version"], "cutoff": cutoff, "rows": rows, "overall": None}
    if rows.empty:
        return result
    X, y = features.split_features_target(rows)
    rows["predicted"] = bundle["pipeline"].predict(X[bundle["feature_columns"]])
    result["rows"] = rows
    result["overall"] = train.evaluate(y, rows["predicted"])
    return result


def breakdown(rows: pd.DataFrame, by) -> pd.DataFrame:
    table = {key: train.evaluate(g[features.TARGET], g["predicted"]) for key, g in rows.groupby(by)}
    return pd.DataFrame(table).T[["rows", "mae", "wape", "bias"]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Score the latest saved model on unseen rows.")
    parser.add_argument("--version", default=None)
    args = parser.parse_args()

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        frame = data.build_training_frame(db)
    result = evaluate_saved_model(frame, version=args.version)
    print(f"Model {result['version']}, trained up to {result['cutoff']}")
    if result["overall"] is None:
        print("No unseen rows: this model was refit on all data. Train with --no-refit to evaluate.")
        return 0
    rows = result["rows"]
    print(f"\nOverall on {len(rows)} unseen rows: {result['overall']}")
    for title, key in (
        ("weekday", rows["date"].dt.day_name()),
        ("location", rows["location_id"].str[:8]),
        ("product", rows["product_id"].str[:8]),
    ):
        print(f"\nBy {title}:\n{breakdown(rows, key).round(3).to_string()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())