from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import PREFIX

STALLS = f"{PREFIX}/stalls"
EVENTS = f"{PREFIX}/events"
NOTIFICATIONS = f"{PREFIX}/notifications"
ORDERS = f"{PREFIX}/orders"
INVENTORY = f"{PREFIX}/inventory"
IST = ZoneInfo("Asia/Kolkata")


def today():
    return datetime.now(IST).date()


def make_location(client, headers) -> str:
    return client.post(
        f"{STALLS}/locations",
        json={"name": "Market Gate", "latitude": 12.97, "longitude": 77.59},
        headers=headers,
    ).json()["id"]


def make_session(client, headers, location_id, day=None, start="09:00:00", end="23:59:00"):
    return client.post(
        f"{STALLS}/sessions",
        json={
            "location_id": location_id,
            "session_date": (day or today()).isoformat(),
            "start_time": start,
            "end_time": end,
        },
        headers=headers,
    )


def set_status(client, headers, sid, new_status):
    return client.patch(
        f"{STALLS}/sessions/{sid}/status", json={"status": new_status}, headers=headers
    )


def schedule_events(client, headers, sid) -> list[dict]:
    """Logged events for one session, oldest first."""
    rows = client.get(f"{EVENTS}?aggregate_id={sid}", headers=headers).json()
    return list(reversed(rows))


def changes(client, headers, sid) -> list[str]:
    return [row["payload"]["change"] for row in schedule_events(client, headers, sid)]


def customer_titles(client, headers) -> list[str]:
    return [n["title"] for n in client.get(f"{NOTIFICATIONS}/me", headers=headers).json()]


def test_creating_a_session_publishes_schedule_updated(client, admin_headers):
    sid = make_session(client, admin_headers, make_location(client, admin_headers)).json()["id"]

    rows = schedule_events(client, admin_headers, sid)
    assert [r["event_type"] for r in rows] == ["stall.schedule_updated"]
    payload = rows[0]["payload"]
    assert payload["change"] == "created"
    assert payload["location_name"] == "Market Gate"
    assert payload["session_date"] == today().isoformat()
    assert payload["start_time"] == "09:00:00"
    assert payload["status"] == "scheduled"


def test_customers_are_told_about_a_new_schedule(client, admin_headers, customer_headers):
    make_session(client, admin_headers, make_location(client, admin_headers))

    notes = client.get(f"{NOTIFICATIONS}/me", headers=customer_headers).json()
    assert [n["title"] for n in notes] == ["New stall schedule"]
    assert notes[0]["audience"] == "all_customers"
    assert notes[0]["status"] == "pending"
    assert "Market Gate" in notes[0]["body"]


def test_status_changes_flow_through_the_event_system(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers, make_location(client, admin_headers)).json()["id"]
    set_status(client, admin_headers, sid, "open")
    set_status(client, admin_headers, sid, "closed")

    assert changes(client, admin_headers, sid) == ["created", "opened", "closed"]
    titles = customer_titles(client, customer_headers)
    assert sorted(titles) == ["New stall schedule", "The stall is open"]  # closing is logged only


def test_cancelling_a_session_notifies_customers(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers, make_location(client, admin_headers)).json()["id"]
    set_status(client, admin_headers, sid, "cancelled")

    assert changes(client, admin_headers, sid) == ["created", "cancelled"]
    assert "Stall visit cancelled" in customer_titles(client, customer_headers)


def test_updating_a_session_publishes_only_when_something_changed(client, admin_headers):
    sid = make_session(client, admin_headers, make_location(client, admin_headers)).json()["id"]
    path = f"{STALLS}/sessions/{sid}"

    assert client.patch(path, json={"notes": "Festival rush"}, headers=admin_headers).status_code == 200
    assert client.patch(path, json={"notes": "Festival rush"}, headers=admin_headers).status_code == 200
    assert client.patch(path, json={}, headers=admin_headers).status_code == 200

    assert changes(client, admin_headers, sid) == ["created", "updated"]  # repeats are not announced


def test_deleting_a_session_publishes_deleted(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers, make_location(client, admin_headers)).json()["id"]

    assert client.delete(f"{STALLS}/sessions/{sid}", headers=admin_headers).status_code == 204

    assert changes(client, admin_headers, sid) == ["created", "deleted"]
    assert "Stall schedule removed" in customer_titles(client, customer_headers)


def test_rejected_changes_publish_nothing(client, admin_headers):
    location_id = make_location(client, admin_headers)
    assert make_session(client, admin_headers, location_id).status_code == 201

    duplicate = make_session(client, admin_headers, location_id)
    past = make_session(client, admin_headers, location_id, day=today() - timedelta(days=1))
    bad_times = make_session(client, admin_headers, location_id, start="18:00:00", end="10:00:00")

    assert (duplicate.status_code, past.status_code, bad_times.status_code) == (409, 400, 422)
    assert len(client.get(EVENTS, headers=admin_headers).json()) == 1  # only the valid create


def test_a_customer_cannot_cause_schedule_events(client, admin_headers, customer_headers):
    location_id = make_location(client, admin_headers)
    assert make_session(client, customer_headers, location_id).status_code == 403
    assert client.get(EVENTS, headers=admin_headers).json() == []


def test_a_session_with_orders_cannot_be_deleted(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers, make_location(client, admin_headers)).json()["id"]
    pid = client.post(
        f"{PREFIX}/products",
        json={"name": "Classic Nankhatai", "price": "120.00"},
        headers=admin_headers,
    ).json()["id"]
    client.put(
        f"{INVENTORY}/sessions/{sid}/products/{pid}",
        json={"stocked_qty": 10},
        headers=admin_headers,
    )
    order = client.post(
        ORDERS,
        json={"session_id": sid, "items": [{"product_id": pid, "quantity": 1}]},
        headers=customer_headers,
    )
    assert order.status_code == 201

    response = client.delete(f"{STALLS}/sessions/{sid}", headers=admin_headers)

    assert response.status_code == 409
    assert "Cancel it instead" in response.json()["detail"]
    assert len(client.get(f"{STALLS}/sessions", headers=admin_headers).json()) == 1
    assert changes(client, admin_headers, sid) == ["created"]  # no "deleted" was announced