import threading
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.events import bus
from app.modules.orders.events import OrderCreated
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.orders.service import create_order
from app.modules.users.models import User
from tests.conftest import PREFIX, TestingSession

ORDERS = f"{PREFIX}/orders"
EVENTS = f"{PREFIX}/events"
NOTIFICATIONS = f"{PREFIX}/notifications"
INVENTORY = f"{PREFIX}/inventory"
IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def listen():
    """Attach a temporary handler to the real bus and remove it afterwards."""
    added = []

    def add(event_class, handler, critical=False, name="test.listener"):
        bus.subscribe(event_class, handler, critical=critical, name=name)
        added.append((event_class, name))

    yield add
    for event_class, name in added:
        bus.unsubscribe(event_class, name)


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


def setup(client, admin_headers, qty=10):
    sid = make_session(client, admin_headers)
    pid = client.post(
        f"{PREFIX}/products",
        json={"name": "Classic Nankhatai", "price": "120.00"},
        headers=admin_headers,
    ).json()["id"]
    client.put(
        f"{INVENTORY}/sessions/{sid}/products/{pid}",
        json={"stocked_qty": qty},
        headers=admin_headers,
    )
    return sid, pid


def stock_row(client, headers, sid, pid) -> dict:
    rows = client.get(f"{INVENTORY}/sessions/{sid}/admin", headers=headers).json()
    return next(r for r in rows if r["product_id"] == pid)


def place(client, headers, sid, items):
    return client.post(
        ORDERS,
        json={"session_id": sid, "items": [{"product_id": p, "quantity": q} for p, q in items]},
        headers=headers,
    )


def logged(client, headers, **filters):
    params = {key: value for key, value in filters.items() if value}
    return client.get(EVENTS, params=params, headers=headers).json()


def admin_alerts(client, headers):
    return client.get(f"{NOTIFICATIONS}?audience=admins", headers=headers).json()


# ---------------- OrderCreated ----------------
def test_placing_an_order_publishes_order_created(client, admin_headers, customer_headers, listen):
    seen = []
    listen(OrderCreated, lambda db, event: seen.append(event), name="test.recorder")
    sid, pid = setup(client, admin_headers)

    order = place(client, customer_headers, sid, [(pid, 3)]).json()

    assert len(seen) == 1
    event = seen[0]
    assert str(event.order_id) == order["id"]
    assert event.customer_name == "Test customer"
    assert event.location_name == "Market Gate"
    assert event.total_amount == Decimal("360.00")
    assert [(line.product_name, line.quantity) for line in event.items] == [("Classic Nankhatai", 3)]


def test_the_inventory_handler_reserves_the_stock(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=10)
    place(client, customer_headers, sid, [(pid, 3)])

    row = stock_row(client, admin_headers, sid, pid)
    assert row["sold_qty"] == 3
    assert row["available_qty"] == 7


def test_order_created_is_written_to_the_event_log(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 3)]).json()["id"]

    rows = logged(client, admin_headers, aggregate_id=order_id)
    assert [r["event_type"] for r in rows] == ["order.created"]
    payload = rows[0]["payload"]
    assert payload["total_amount"] == "360.00"
    assert payload["session_id"] == sid
    assert payload["location_name"] == "Market Gate"
    assert payload["items"][0]["quantity"] == 3
    assert payload["items"][0]["unit_price"] == "120.00"


def test_order_created_queues_notifications(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    place(client, customer_headers, sid, [(pid, 3)])

    mine = client.get(f"{NOTIFICATIONS}/me", headers=customer_headers).json()
    placed = next(n for n in mine if n["title"] == "Order placed")
    assert placed["status"] == "pending"  # queued, not sent: no Firebase yet
    assert "Market Gate" in placed["body"]

    alerts = admin_alerts(client, admin_headers)
    assert [n["title"] for n in alerts] == ["New order"]
    assert "Test customer ordered 3 item(s)" in alerts[0]["body"]

    admin_feed = {n["title"] for n in client.get(f"{NOTIFICATIONS}/me", headers=admin_headers).json()}
    assert "New order" in admin_feed
    assert "New stall schedule" not in admin_feed  # that one is for customers


# ---------------- OrderCancelled ----------------
def test_cancelling_publishes_order_cancelled_and_returns_stock(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=10)
    order_id = place(client, customer_headers, sid, [(pid, 4)]).json()["id"]
    assert stock_row(client, admin_headers, sid, pid)["available_qty"] == 6

    cancel = f"{ORDERS}/me/{order_id}/cancel"
    assert client.post(cancel, headers=customer_headers).status_code == 200
    assert stock_row(client, admin_headers, sid, pid)["available_qty"] == 10
    assert client.post(cancel, headers=customer_headers).status_code == 409  # nothing published again

    rows = logged(client, admin_headers, aggregate_id=order_id)
    assert sorted(r["event_type"] for r in rows) == ["order.cancelled", "order.created"]
    cancelled = next(r for r in rows if r["event_type"] == "order.cancelled")
    assert cancelled["payload"]["cancelled_by"] == "customer"
    assert cancelled["payload"]["items"][0]["quantity"] == 4

    titles = {n["title"] for n in client.get(f"{NOTIFICATIONS}/me", headers=customer_headers).json()}
    assert "Order cancelled" in titles


def test_admin_cancellation_is_recorded_as_such(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers)
    order_id = place(client, customer_headers, sid, [(pid, 1)]).json()["id"]

    response = client.patch(
        f"{ORDERS}/{order_id}/status", json={"status": "cancelled"}, headers=admin_headers
    )
    assert response.status_code == 200

    rows = logged(client, admin_headers, event_type="order.cancelled")
    assert rows[0]["payload"]["cancelled_by"] == "admin"


# ---------------- failure behaviour ----------------
def test_a_failed_order_publishes_nothing(client, admin_headers, customer_headers):
    sid, pid = setup(client, admin_headers, qty=2)

    response = place(client, customer_headers, sid, [(pid, 3)])
    assert response.status_code == 409
    assert "Only 2 left" in response.json()["detail"]

    assert logged(client, admin_headers, event_type="order.created") == []
    assert admin_alerts(client, admin_headers) == []
    assert stock_row(client, admin_headers, sid, pid)["sold_qty"] == 0


def test_a_failing_critical_handler_rolls_back_the_whole_order(client, admin_headers, customer_headers, listen):
    sid, pid = setup(client, admin_headers, qty=10)

    def refuse(db, event):
        raise HTTPException(409, "Refused by test")

    # Registered after the inventory handler, so the stock is already reserved when this fails.
    listen(OrderCreated, refuse, critical=True, name="test.refuse")
    response = place(client, customer_headers, sid, [(pid, 2)])

    assert response.status_code == 409
    assert response.json()["detail"] == "Refused by test"
    assert stock_row(client, admin_headers, sid, pid)["sold_qty"] == 0  # reservation undone
    assert client.get(f"{ORDERS}/me", headers=customer_headers).json() == []
    assert logged(client, admin_headers, event_type="order.created") == []
    assert admin_alerts(client, admin_headers) == []


def test_a_failing_side_effect_handler_does_not_block_the_order(client, admin_headers, customer_headers, listen):
    sid, pid = setup(client, admin_headers, qty=10)

    def explode(db, event):
        raise RuntimeError("push service down")

    listen(OrderCreated, explode, name="test.explode")
    response = place(client, customer_headers, sid, [(pid, 2)])

    assert response.status_code == 201
    assert stock_row(client, admin_headers, sid, pid)["sold_qty"] == 2
    assert len(logged(client, admin_headers, event_type="order.created")) == 1  # other handlers still ran


def test_events_do_not_break_the_no_oversell_guarantee(client, admin_headers, customer_headers):
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

    assert sum(outcomes) == 5
    assert stock_row(client, admin_headers, sid, pid)["sold_qty"] == 5
    rows = client.get(
        EVENTS, params={"event_type": "order.created", "limit": 100}, headers=admin_headers
    ).json()
    assert len(rows) == 5  # exactly one event per order that really happened
    assert len(client.get(f"{NOTIFICATIONS}?audience=admins&limit=100", headers=admin_headers).json()) == 5


# ---------------- access ----------------
def test_event_log_and_notification_admin_views_are_admin_only(client, customer_headers):
    assert client.get(EVENTS, headers=customer_headers).status_code == 403
    assert client.get(NOTIFICATIONS, headers=customer_headers).status_code == 403
    assert client.get(f"{NOTIFICATIONS}/me", headers=customer_headers).status_code == 200
    assert client.get(EVENTS).status_code in (401, 403)