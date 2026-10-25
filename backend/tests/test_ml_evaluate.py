import pandas as pd
import pytest

from app.ml import evaluate, features, train
from tests.test_ml_train import synthetic_daily


@pytest.fixture(scope="module")
def history():
    return features.build_feature_frame(synthetic_daily())


def test_only_unseen_rows_are_scored(history, tmp_path):
    result = train.train_and_save(history, artifact_dir=tmp_path, validation_days=14, refit_on_all=False)
    out = evaluate.evaluate_saved_model(history, artifact_dir=tmp_path)

    split = result.metadata["split"]
    assert out["rows"]["date"].min() > pd.Timestamp(split["train_end"])
    assert len(out["rows"]) == split["validation_rows"]
    assert out["overall"]["mae"] == pytest.approx(result.metadata["validation"]["model"]["mae"], abs=1e-3)


def test_nothing_is_unseen_after_refit(history, tmp_path):
    train.train_and_save(history, artifact_dir=tmp_path, validation_days=14)
    out = evaluate.evaluate_saved_model(history, artifact_dir=tmp_path)
    assert out["rows"].empty and out["overall"] is None


def test_breakdown_has_one_row_per_group(history, tmp_path):
    train.train_and_save(history, artifact_dir=tmp_path, validation_days=14, refit_on_all=False)
    rows = evaluate.evaluate_saved_model(history, artifact_dir=tmp_path)["rows"]
    table = evaluate.breakdown(rows, rows["location_id"])
    assert set(table.index) == {"loc-a", "loc-b"}
    assert table["rows"].sum() == len(rows)