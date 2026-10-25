from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tests.conftest import PREFIX

A = f"{PREFIX}/analytics"
ORDERS = f"{PREFIX}/orders"


def setup(client, h):
    loc = client.post(
        f"{PREFIX}/stalls/locations",
        json={"name": "Market Gate", "latitude": 12.97, "longitude": 77.59},
        headers=h,
    ).json()["id"]
    sid = client.post(
        f"{PREFIX}/stalls/sessions",
        json={
            "location_id": loc,
            "session_date": datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(),
            "start_time": "09:00:00",
            "end_time": "23:59:00",
        },
        headers=h,
    ).json()["id"]
    pid = client.post(
        f"{PREFIX}/products", json={"name": "Classic Nankhatai", "price": "120.00"}, headers=h
    ).json()["id"]
    client.put(f"{PREFIX}/inventory/sessions/{sid}/products/{pid}", json={"stocked_qty": 10}, headers=h)
    return sid, pid


def order(client, admin, customer, sid, pid, qty, finish=True):
    oid = client.post(
        ORDERS,
        json={"session_id": sid, "items": [{"product_id": pid, "quantity": qty}]},
        headers=customer,
    ).json()["id"]
    if finish:
        for status in ("confirmed", "preparing", "ready", "completed"):
            client.patch(f"{ORDERS}/{oid}/status", json={"status": status}, headers=admin)
    return oid


@pytest.mark.parametrize("name", ["summary", "sales", "products", "locations"])
def test_admin_only(client, admin_headers, customer_headers, name):
    assert client.get(f"{A}/{name}", headers=customer_headers).status_code == 403
    assert client.get(f"{A}/{name}").status_code in (401, 403)
    assert client.get(f"{A}/{name}", headers=admin_headers).status_code == 200


def test_empty_database(client, admin_headers):
    body = client.get(f"{A}/summary", headers=admin_headers).json()
    assert body["revenue"] == 0 and body["orders"] == 0 and body["sell_through"] == 0
    for name in ("sales", "products", "locations"):
        assert client.get(f"{A}/{name}", headers=admin_headers).json() == []


def test_only_completed_orders_count_as_revenue(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order(client, admin_headers, customer_headers, sid, pid, 3)
    order(client, admin_headers, customer_headers, sid, pid, 2, finish=False)

    body = client.get(f"{A}/summary", headers=admin_headers).json()
    assert body["revenue"] == 360 and body["orders"] == 1
    assert body["stocked"] == 10 and body["sold"] == 5 and body["sell_through"] == 0.5


def test_expenses_reduce_profit(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order(client, admin_headers, customer_headers, sid, pid, 3)
    client.post(f"{PREFIX}/expenses", json={"amount": "100.00", "category": "fuel"}, headers=admin_headers)

    body = client.get(f"{A}/summary", headers=admin_headers).json()
    assert body["expenses"] == 100 and body["profit"] == 260


def test_sales_products_and_locations(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order(client, admin_headers, customer_headers, sid, pid, 3)

    sales = client.get(f"{A}/sales", headers=admin_headers).json()
    assert [(s["revenue"], s["orders"]) for s in sales] == [(360, 1)]
    top = client.get(f"{A}/products", headers=admin_headers).json()
    assert top == [{"name": "Classic Nankhatai", "units": 3, "revenue": 360}]
    where = client.get(f"{A}/locations", headers=admin_headers).json()
    assert where == [{"name": "Market Gate", "revenue": 360, "orders": 1}]


def test_days_must_be_in_range(client, admin_headers):
    assert client.get(f"{A}/summary?days=0", headers=admin_headers).status_code == 422
    assert client.get(f"{A}/summary?days=366", headers=admin_headers).status_code == 422