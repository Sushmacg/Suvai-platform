import threading
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.orders.service import create_order
from app.modules.users.models import User
from tests.conftest import PREFIX, TestingSession, _headers_for

ORDERS = f"{PREFIX}/orders"
IST = ZoneInfo("Asia/Kolkata")


# ---------------- helpers ----------------
def make_session(client, headers) -> str:
    location = client.post(
        f"{PREFIX}/stalls/locations",
        json={"name": "Market Gate", "latitude": 12.97, "longitude": 77.59},
        headers=headers,
    ).json()["id"]
    return client.post(
        f"{PREFIX}/stalls/sessions",
        json={
            "location_id": location,
            "session_date": datetime.now(IST).date().isoformat(),
            "start_time": "09:00:00",
            "end_time": "23:59:00",
        },
        headers=headers,
    ).json()["id"]


def make_product(client, headers, name="Classic Nankhatai", price="120.00") -> str:
    return client.post(
        f"{PREFIX}/products", json={"name": name, "price": price}, headers=headers
    ).json()["id"]


def put_stock(client, headers, session_id, product_id, qty):
    return client.put(
        f"{PREFIX}/inventory/sessions/{session_id}/products/{product_id}",
        json={"stocked_qty": qty},
        headers=headers,
    )


def stock_row(client, headers, session_id, product_id) -> dict:
    rows = client.get(
        f"{PREFIX}/inventory/sessions/{session_id}/admin", headers=headers
    ).json()
    return next(r for r in rows if r["product_id"] == product_id)


def place(client, headers, session_id, items, **extra):
    return client.post(
        ORDERS,
        json={
            "session_id": session_id,
            "items": [{"product_id": p, "quantity": q} for p, q in items],
            **extra,
        },
        headers=headers,
    )


def set_status(client, headers, order_id, new_status):
    return client.patch(
        f"{ORDERS}/{order_id}/status", json={"status": new_status}, headers=headers
    )


def setup(client, admin_headers, qty=10):
    """A session with one stocked product."""
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, qty)
    return sid, pid


# ---------------- placing orders ----------------
def test_customer_places_order(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)

    response = place(client, customer_headers, sid, [(pid, 3)], notes="Extra crisp")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert Decimal(body["total_amount"]) == Decimal("360.00")
    assert body["notes"] == "Extra crisp"
    assert body["items"][0]["product_name"] == "Classic Nankhatai"
    assert body["items"][0]["quantity"] == 3
    assert Decimal(body["items"][0]["line_total"]) == Decimal("360.00")
    assert body["session"]["location"]["name"] == "Market Gate"  # pickup details

    row = stock_row(client, admin_headers, sid, pid)
    assert row["sold_qty"] == 3
    assert row["available_qty"] == 7


def test_anonymous_cannot_order(client, admin_headers):
    sid, pid = setup(client, admin_headers)
    assert place(client, {}, sid, [(pid, 1)]).status_code in (401, 403)


def test_order_with_several_products(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers)
    plain = make_product(client, admin_headers, "Plain", "120.00")
    salty = make_product(client, admin_headers, "Salty", "90.00")
    put_stock(client, admin_headers, sid, plain, 10)
    put_stock(client, admin_headers, sid, salty, 10)

    response = place(client, customer_headers, sid, [(plain, 2), (salty, 1)])
    assert response.status_code == 201
    assert Decimal(response.json()["total_amount"]) == Decimal("330.00")
    assert stock_row(client, admin_headers, sid, plain)["sold_qty"] == 2
    assert stock_row(client, admin_headers, sid, salty)["sold_qty"] == 1


def test_duplicate_items_are_merged(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    response = place(client, customer_headers, sid, [(pid, 2), (pid, 3)])
    assert response.status_code == 201
    items = response.json()["items"]
    assert len(items) == 1 and items[0]["quantity"] == 5


def test_price_is_frozen_at_order_time(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 2)]).json()["id"]

    client.patch(f"{PREFIX}/products/{pid}", json={"price": "200.00"}, headers=admin_headers)

    order = client.get(f"{ORDERS}/me/{order_id}", headers=customer_headers).json()
    assert Decimal(order["items"][0]["unit_price"]) == Decimal("120.00")
    assert Decimal(order["total_amount"]) == Decimal("240.00")


# ---------------- inventory rules ----------------
def test_cannot_order_more_than_available(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=2)

    response = place(client, customer_headers, sid, [(pid, 3)])
    assert response.status_code == 409
    assert "Only 2 left" in response.json()["detail"]
    assert stock_row(client, admin_headers, sid, pid)["sold_qty"] == 0
    assert client.get(f"{ORDERS}/me", headers=customer_headers).json() == []


def test_failed_multi_item_order_leaves_no_trace(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers)
    first = make_product(client, admin_headers, "Plain")
    second = make_product(client, admin_headers, "Salty")
    put_stock(client, admin_headers, sid, first, 10)
    put_stock(client, admin_headers, sid, second, 1)

    response = place(client, customer_headers, sid, [(first, 2), (second, 5)])
    assert response.status_code == 409
    assert stock_row(client, admin_headers, sid, first)["sold_qty"] == 0  # rolled back
    assert stock_row(client, admin_headers, sid, second)["sold_qty"] == 0
    assert client.get(f"{ORDERS}/me", headers=customer_headers).json() == []


def test_can_buy_the_last_item_and_then_no_more(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=2)
    assert place(client, customer_headers, sid, [(pid, 2)]).status_code == 201
    assert place(client, customer_headers, sid, [(pid, 1)]).status_code == 409


def test_unstocked_product_rejected(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)  # never stocked
    response = place(client, customer_headers, sid, [(pid, 1)])
    assert response.status_code == 409
    assert "not stocked" in response.json()["detail"]


def test_sold_out_product_rejected(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    client.patch(f"{PREFIX}/products/{pid}", json={"is_available": False}, headers=admin_headers)
    assert place(client, customer_headers, sid, [(pid, 1)]).status_code == 409


def test_unknown_or_removed_product_rejected(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    missing = "00000000-0000-0000-0000-000000000000"
    assert place(client, customer_headers, sid, [(missing, 1)]).status_code == 404

    client.delete(f"{PREFIX}/products/{pid}", headers=admin_headers)
    assert place(client, customer_headers, sid, [(pid, 1)]).status_code == 404


# ---------------- session rules ----------------
def test_unknown_session_rejected(client, admin_headers, customer_headers):
    _, pid = setup(client, admin_headers)
    missing = "00000000-0000-0000-0000-000000000000"
    assert place(client, customer_headers, missing, [(pid, 1)]).status_code == 404


def test_closed_session_rejected(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    for new_status in ("open", "closed"):
        client.patch(
            f"{PREFIX}/stalls/sessions/{sid}/status",
            json={"status": new_status},
            headers=admin_headers,
        )
    assert place(client, customer_headers, sid, [(pid, 1)]).status_code == 409


def test_open_session_accepts_orders(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    client.patch(
        f"{PREFIX}/stalls/sessions/{sid}/status",
        json={"status": "open"},
        headers=admin_headers,
    )
    assert place(client, customer_headers, sid, [(pid, 1)]).status_code == 201


def test_past_session_rejected(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    with TestingSession() as db:
        db.execute(text("UPDATE stall_sessions SET session_date = session_date - 1"))
        db.commit()
    assert place(client, customer_headers, sid, [(pid, 1)]).status_code == 409


# ---------------- input validation ----------------
def test_invalid_orders_rejected(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    assert place(client, customer_headers, sid, []).status_code == 422
    assert place(client, customer_headers, sid, [(pid, 0)]).status_code == 422
    assert place(client, customer_headers, sid, [(pid, 51)]).status_code == 422
    assert place(client, customer_headers, sid, [(pid, 1)], notes="x" * 301).status_code == 422

    too_many = [(pid, 1)] * 21
    assert place(client, customer_headers, sid, too_many).status_code == 422


def test_merged_quantity_cap(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=500)
    response = place(client, customer_headers, sid, [(pid, 30), (pid, 30)])
    assert response.status_code == 400  # 60 of one product in total


# ---------------- who can see what ----------------
def test_customers_see_only_their_own_orders(client, admin_headers, customer_headers):
    other_headers = _headers_for(client, "9000000003", "customer")
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 1)]).json()["id"]

    assert len(client.get(f"{ORDERS}/me", headers=customer_headers).json()) == 1
    assert client.get(f"{ORDERS}/me", headers=other_headers).json() == []
    assert client.get(f"{ORDERS}/me/{order_id}", headers=other_headers).status_code == 404
    cancel = client.post(f"{ORDERS}/me/{order_id}/cancel", headers=other_headers)
    assert cancel.status_code == 404


def test_admin_sees_all_orders_with_customer_details(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 1)]).json()["id"]

    orders = client.get(ORDERS, headers=admin_headers).json()
    assert len(orders) == 1
    assert orders[0]["customer_phone"] == "9000000002"
    assert client.get(f"{ORDERS}/{order_id}", headers=admin_headers).status_code == 200


def test_customer_cannot_use_admin_order_routes(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 1)]).json()["id"]

    assert client.get(ORDERS, headers=customer_headers).status_code == 403
    assert client.get(f"{ORDERS}/{order_id}", headers=customer_headers).status_code == 403
    assert set_status(client, customer_headers, order_id, "confirmed").status_code == 403


def test_filters_and_pagination(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=50)
    ids = [place(client, customer_headers, sid, [(pid, 1)]).json()["id"] for _ in range(3)]
    set_status(client, admin_headers, ids[0], "confirmed")

    confirmed = client.get(f"{ORDERS}?status=confirmed", headers=admin_headers).json()
    assert [o["id"] for o in confirmed] == [ids[0]]
    by_session = client.get(f"{ORDERS}?session_id={sid}", headers=admin_headers).json()
    assert len(by_session) == 3

    assert len(client.get(f"{ORDERS}/me?limit=2", headers=customer_headers).json()) == 2
    assert len(client.get(f"{ORDERS}/me?limit=2&offset=2", headers=customer_headers).json()) == 1
    assert client.get(f"{ORDERS}?status=bogus", headers=admin_headers).status_code == 422


# ---------------- status flow ----------------
def test_full_status_flow(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 1)]).json()["id"]

    for next_status in ("confirmed", "preparing", "ready", "completed"):
        response = set_status(client, admin_headers, order_id, next_status)
        assert response.status_code == 200
        assert response.json()["status"] == next_status

    assert set_status(client, admin_headers, order_id, "cancelled").status_code == 409


def test_invalid_status_jumps_rejected(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 1)]).json()["id"]

    assert set_status(client, admin_headers, order_id, "ready").status_code == 409
    assert set_status(client, admin_headers, order_id, "completed").status_code == 409
    assert set_status(client, admin_headers, order_id, "pending").status_code == 422


# ---------------- cancelling ----------------
def test_customer_cancels_pending_order_and_stock_returns(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=10)
    order_id = place(client, customer_headers, sid, [(pid, 4)]).json()["id"]
    assert stock_row(client, admin_headers, sid, pid)["available_qty"] == 6

    response = client.post(f"{ORDERS}/me/{order_id}/cancel", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert stock_row(client, admin_headers, sid, pid)["available_qty"] == 10


def test_customer_cannot_cancel_once_confirmed(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 1)]).json()["id"]
    set_status(client, admin_headers, order_id, "confirmed")

    response = client.post(f"{ORDERS}/me/{order_id}/cancel", headers=customer_headers)
    assert response.status_code == 409


def test_admin_cancel_returns_stock_exactly_once(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=10)
    order_id = place(client, customer_headers, sid, [(pid, 4)]).json()["id"]
    set_status(client, admin_headers, order_id, "confirmed")
    set_status(client, admin_headers, order_id, "preparing")

    assert set_status(client, admin_headers, order_id, "cancelled").status_code == 200
    assert stock_row(client, admin_headers, sid, pid)["available_qty"] == 10

    assert set_status(client, admin_headers, order_id, "cancelled").status_code == 409
    assert stock_row(client, admin_headers, sid, pid)["available_qty"] == 10  # not 14


def test_completing_an_order_keeps_stock_sold(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=10)
    order_id = place(client, customer_headers, sid, [(pid, 4)]).json()["id"]
    for next_status in ("confirmed", "preparing", "ready", "completed"):
        set_status(client, admin_headers, order_id, next_status)
    assert stock_row(client, admin_headers, sid, pid)["sold_qty"] == 4


# ---------------- concurrency and database rules ----------------
def test_concurrent_orders_never_oversell(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=5)
    outcomes = []

    def buy_one():
        with TestingSession() as db:
            user = db.scalars(select(User).where(User.phone == "9000000002")).one()
            try:
                create_order(
                    db,
                    user,
                    OrderCreate(
                        session_id=sid,
                        items=[OrderItemCreate(product_id=pid, quantity=1)],
                    ),
                )
                outcomes.append(True)
            except HTTPException:
                outcomes.append(False)

    threads = [threading.Thread(target=buy_one) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(outcomes) == 5  # exactly 5 orders succeed, 7 are refused
    row = stock_row(client, admin_headers, sid, pid)
    assert row["sold_qty"] == 5 and row["available_qty"] == 0
    assert len(client.get(ORDERS, headers=admin_headers).json()) == 5


def test_database_rejects_bad_rows(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    place(client, customer_headers, sid, [(pid, 1)])

    with TestingSession() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE order_items SET quantity = 0"))
            db.commit()
    with TestingSession() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE orders SET status = 'bogus'"))
            db.commit()
