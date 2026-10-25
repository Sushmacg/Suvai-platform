import dataclasses
import json
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import ClassVar

import pytest
from sqlalchemy import select

from app.core.events import DomainEvent, EventBus, bus
from app.modules.notifications.models import Notification
from app.modules.orders.events import OrderCreated, OrderLine
from tests.conftest import TestingSession


@dataclass(frozen=True, kw_only=True)
class Ping(DomainEvent):
    event_type: ClassVar[str] = "test.ping"
    value: int


def test_every_subscriber_receives_the_event():
    local = EventBus()
    received = []
    local.subscribe(Ping, lambda db, e: received.append(("a", e.value)), critical=True, name="a")
    local.subscribe(Ping, lambda db, e: received.append(("b", e.value)), critical=True, name="b")

    local.publish(None, Ping(value=7))

    assert received == [("a", 7), ("b", 7)]


def test_publishing_with_no_subscribers_fails_loudly():
    with pytest.raises(RuntimeError, match="No handlers"):
        EventBus().publish(None, Ping(value=1))


def test_subscribing_twice_is_harmless_and_unsubscribe_works():
    local = EventBus()
    calls = []
    handler = lambda db, e: calls.append(1)  # noqa: E731
    local.subscribe(Ping, handler, critical=True, name="once")
    local.subscribe(Ping, handler, critical=True, name="once")

    local.publish(None, Ping(value=1))
    assert calls == [1]

    local.unsubscribe(Ping, "once")
    with pytest.raises(RuntimeError):
        local.publish(None, Ping(value=1))


def test_critical_handlers_run_before_best_effort_ones():
    local = EventBus()
    order = []
    local.subscribe(Ping, lambda d, e: order.append("best-effort"), name="late")
    local.subscribe(Ping, lambda d, e: order.append("critical"), critical=True, name="early")

    with TestingSession() as db:
        local.publish(db, Ping(value=1))

    assert order == ["critical", "best-effort"]


def test_a_critical_failure_stops_everything_and_propagates():
    local = EventBus()
    ran = []

    def boom(db, event):
        raise ValueError("no stock")

    local.subscribe(Ping, boom, critical=True, name="boom")
    local.subscribe(Ping, lambda d, e: ran.append("after"), name="after")

    with TestingSession() as db:
        with pytest.raises(ValueError, match="no stock"):
            local.publish(db, Ping(value=1))

    assert ran == []


def test_a_best_effort_failure_is_isolated_and_its_changes_are_undone():
    local = EventBus()

    def broken(db, event):
        db.add(Notification(event_type="test", audience="admins", title="from broken", body="x"))
        raise RuntimeError("push service down")

    def healthy(db, event):
        db.add(Notification(event_type="test", audience="admins", title="from healthy", body="x"))

    local.subscribe(Ping, broken, name="broken")
    local.subscribe(Ping, healthy, name="healthy")

    with TestingSession() as db:
        local.publish(db, Ping(value=1))  # does not raise
        db.commit()
        titles = db.scalars(select(Notification.title)).all()

    assert titles == ["from healthy"]


def test_event_payload_is_json_safe():
    event = OrderCreated(
        order_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        customer_name="Asha",
        session_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        location_name="Market Gate",
        session_date=date(2026, 10, 11),
        total_amount=Decimal("360.00"),
        items=(
            OrderLine(
                product_id=uuid.uuid4(),
                product_name="Classic Nankhatai",
                quantity=3,
                unit_price=Decimal("120.00"),
            ),
        ),
    )
    payload = event.payload()

    json.dumps(payload)  # raises if anything is not plain JSON
    assert payload["total_amount"] == "360.00"
    assert payload["session_date"] == "2026-10-11"
    assert payload["items"][0]["quantity"] == 3
    assert payload["items"][0]["unit_price"] == "120.00"
    assert "event_id" not in payload
    assert event.aggregate_id == event.order_id


def test_each_event_gets_its_own_id_and_a_utc_timestamp():
    first, second = Ping(value=1), Ping(value=1)
    assert first.event_id != second.event_id
    assert first.occurred_at.tzinfo is not None


def test_events_are_immutable():
    event = Ping(value=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.value = 2


def test_all_handlers_are_wired_at_startup():
    import app.main  # noqa: F401  (registers the handlers)

    wiring = bus.describe()
    created = wiring["order.created"]
    assert any("reserve_stock_for_order" in h and "(critical)" in h for h in created)
    assert any("record_event" in h and "(best-effort)" in h for h in created)
    assert any("on_order_created" in h for h in created)

    cancelled = wiring["order.cancelled"]
    assert any("release_stock_for_order" in h and "(critical)" in h for h in cancelled)

    schedule = wiring["stall.schedule_updated"]
    assert any("record_event" in h for h in schedule)
    assert any("on_stall_schedule_updated" in h for h in schedule)