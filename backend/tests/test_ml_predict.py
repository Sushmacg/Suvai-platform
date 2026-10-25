from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.ml import features, predict

TODAY = date(2026, 10, 26)


class FakePipeline:
    def predict(self, X):
        return np.array([-1.0, 2.345][: len(X)])


def _frame(n=2):
    df = pd.DataFrame({c: [0.0] * n for c in features.FEATURE_COLUMNS})
    for c in features.CATEGORICAL_FEATURES:
        df[c] = "x"
    df["date"] = pd.Timestamp(TODAY)
    df["location_id"] = [f"loc-{i}" for i in range(n)]
    df["product_id"] = [f"prod-{i}" for i in range(n)]
    return df


@pytest.fixture
def fake_model(monkeypatch):
    monkeypatch.setattr(predict, "_load", lambda d: ({"pipeline": FakePipeline(), "version": "v1"}, {}))
    monkeypatch.setattr(predict.data, "build_prediction_frame", lambda *a, **k: _frame())


def test_predictions_are_clipped_rounded_and_shaped(fake_model):
    result = predict.forecast_demand(None, TODAY, today=TODAY)
    assert result.model_version == "v1"
    assert [r["predicted_units"] for r in result.rows] == [0.0, 2.35]
    assert set(result.rows[0]) == {"date", "location_id", "product_id", "predicted_units"}
    assert result.rows[0]["date"] == TODAY


def test_empty_frame_returns_no_rows(fake_model, monkeypatch):
    monkeypatch.setattr(predict.data, "build_prediction_frame", lambda *a, **k: _frame(0))
    assert predict.forecast_demand(None, TODAY, today=TODAY).rows == []


def test_missing_artifact_is_reported(tmp_path):
    with pytest.raises(predict.ModelUnavailableError):
        predict.forecast_demand(None, TODAY, artifact_dir=tmp_path, today=TODAY)


@pytest.mark.parametrize("bad", [date(2026, 10, 25), date(2026, 11, 20)])
def test_invalid_dates_are_rejected(fake_model, bad):
    with pytest.raises(predict.InvalidForecastRequest):
        predict.forecast_demand(None, bad, today=TODAY)