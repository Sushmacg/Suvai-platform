import uuid
from datetime import timedelta

import pytest

from app.ml import predict
from app.modules.stalls.service import today_ist
from tests.conftest import PREFIX

F = f"{PREFIX}/forecasts"


def fake_forecast(db, target_date, location_ids=None, product_ids=None, **kw):
    row = {
        "date": target_date,
        "location_id": str(uuid.uuid4()),
        "product_id": str(uuid.uuid4()),
        "predicted_units": 4.25,
    }
    return predict.ForecastResult("v-test", [row])


def test_admin_only(client, admin_headers, customer_headers, monkeypatch):
    monkeypatch.setattr(predict, "forecast_demand", fake_forecast)
    assert client.get(F, headers=customer_headers).status_code == 403
    assert client.get(F).status_code in (401, 403)
    assert client.get(F, headers=admin_headers).status_code == 200


def test_response_schema(client, admin_headers, monkeypatch):
    monkeypatch.setattr(predict, "forecast_demand", fake_forecast)
    day = (today_ist() + timedelta(days=1)).isoformat()
    body = client.get(f"{F}?date={day}", headers=admin_headers).json()
    assert set(body) == {"model_version", "forecast_date", "items"}
    assert body["model_version"] == "v-test" and body["forecast_date"] == day
    assert set(body["items"][0]) == {"date", "location_id", "product_id", "predicted_units"}
    assert body["items"][0]["predicted_units"] == 4.25


def test_default_date_is_tomorrow(client, admin_headers, monkeypatch):
    monkeypatch.setattr(predict, "forecast_demand", fake_forecast)
    body = client.get(F, headers=admin_headers).json()
    assert body["forecast_date"] == (today_ist() + timedelta(days=1)).isoformat()


@pytest.mark.parametrize("query", ["date=not-a-date", "location_id=abc", "product_id=123"])
def test_malformed_input_is_422(client, admin_headers, query):
    assert client.get(f"{F}?{query}", headers=admin_headers).status_code == 422


def test_past_and_far_future_dates_are_400(client, admin_headers):
    past = (today_ist() - timedelta(days=1)).isoformat()
    far = (today_ist() + timedelta(days=60)).isoformat()
    assert client.get(f"{F}?date={past}", headers=admin_headers).status_code == 400
    assert client.get(f"{F}?date={far}", headers=admin_headers).status_code == 400


def test_missing_model_is_503_without_leaking_paths(client, admin_headers, monkeypatch):
    def boom(*a, **k):
        raise predict.ModelUnavailableError(r"C:\secret\path\latest.json not found")

    monkeypatch.setattr(predict, "forecast_demand", boom)
    r = client.get(F, headers=admin_headers)
    assert r.status_code == 503
    assert "secret" not in r.text