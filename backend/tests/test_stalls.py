from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.modules.stalls.service import haversine_km
from tests.conftest import PREFIX

URL = f"{PREFIX}/stalls"
IST = ZoneInfo("Asia/Kolkata")


def today():
    return datetime.now(IST).date()


def make_location(client, headers, name="Market Gate", lat=12.9716, lng=77.5946):
    return client.post(
        f"{URL}/locations",
        json={"name": name, "address": "Main Road", "latitude": lat, "longitude": lng},
        headers=headers,
    )


def make_session(client, headers, location_id, day=None, start="09:00:00", end="23:59:00", **extra):
    day = day or today()
    return client.post(
        f"{URL}/sessions",
        json={
            "location_id": location_id,
            "session_date": day.isoformat(),
            "start_time": start,
            "end_time": end,
            **extra,
        },
        headers=headers,
    )


def set_status(client, headers, session_id, new_status):
    return client.patch(
        f"{URL}/sessions/{session_id}/status", json={"status": new_status}, headers=headers
    )


# ---------------- locations ----------------
def test_admin_creates_location(client, admin_headers):
    response = make_location(client, admin_headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Market Gate"


def test_customer_cannot_create_location(client, customer_headers):
    assert make_location(client, customer_headers).status_code == 403


@pytest.mark.parametrize("lat,lng", [(91, 77), (-91, 77), (12, 181), (12, -181)])
def test_invalid_coordinates_rejected(client, admin_headers, lat, lng):
    assert make_location(client, admin_headers, lat=lat, lng=lng).status_code == 422


def test_inactive_locations_hidden_from_public(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    assert client.delete(f"{URL}/locations/{location_id}", headers=admin_headers).status_code == 204

    assert client.get(f"{URL}/locations").json() == []
    everything = client.get(f"{URL}/locations/all", headers=admin_headers).json()
    assert everything[0]["is_active"] is False


def test_admin_updates_location(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    response = client.patch(
        f"{URL}/locations/{location_id}", json={"name": "Bus Stand"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Bus Stand"


def test_cannot_deactivate_location_with_active_session(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]

    response = client.delete(f"{URL}/locations/{location_id}", headers=admin_headers)
    assert response.status_code == 409

    set_status(client, admin_headers, session_id, "cancelled")
    response = client.delete(f"{URL}/locations/{location_id}", headers=admin_headers)
    assert response.status_code == 204


# ---------------- sessions: create and validate ----------------
def test_admin_creates_session(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    response = make_session(client, admin_headers, location_id)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["location"]["name"] == "Market Gate"


def test_customer_cannot_create_session(client, admin_headers, customer_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    assert make_session(client, customer_headers, location_id).status_code == 403


def test_end_before_start_rejected(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    response = make_session(client, admin_headers, location_id, start="18:00:00", end="10:00:00")
    assert response.status_code == 422


def test_past_date_rejected(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    yesterday = today() - timedelta(days=1)
    assert make_session(client, admin_headers, location_id, day=yesterday).status_code == 400


def test_unknown_location_rejected(client, admin_headers):
    missing = "00000000-0000-0000-0000-000000000000"
    assert make_session(client, admin_headers, missing).status_code == 404


def test_duplicate_slot_rejected(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    assert make_session(client, admin_headers, location_id).status_code == 201
    assert make_session(client, admin_headers, location_id).status_code == 409


# ---------------- sessions: public views ----------------
def test_today_and_upcoming(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    make_session(client, admin_headers, location_id)
    make_session(client, admin_headers, location_id, day=today() + timedelta(days=1))

    assert len(client.get(f"{URL}/today").json()) == 1
    assert len(client.get(f"{URL}/upcoming?days=7").json()) == 2


def test_current_is_none_when_nothing_scheduled(client):
    body = client.get(f"{URL}/current").json()
    assert body == {"state": "none", "session": None}


def test_current_shows_next_upcoming_session(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    make_session(client, admin_headers, location_id, day=today() + timedelta(days=1))

    body = client.get(f"{URL}/current").json()
    assert body["state"] == "upcoming"
    assert body["session"]["location"]["name"] == "Market Gate"


def test_current_shows_open_session(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]
    set_status(client, admin_headers, session_id, "open")

    body = client.get(f"{URL}/current").json()
    assert body["state"] == "open"
    assert body["session"]["id"] == session_id


# ---------------- sessions: status rules ----------------
def test_status_flow(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]

    assert set_status(client, admin_headers, session_id, "open").json()["status"] == "open"
    assert set_status(client, admin_headers, session_id, "closed").json()["status"] == "closed"
    assert set_status(client, admin_headers, session_id, "open").status_code == 409


def test_invalid_status_value_rejected(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]
    assert set_status(client, admin_headers, session_id, "scheduled").status_code == 422


def test_only_one_session_can_be_open(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    first = make_session(client, admin_headers, location_id).json()["id"]
    second = make_session(client, admin_headers, location_id, start="10:00:00").json()["id"]

    assert set_status(client, admin_headers, first, "open").status_code == 200
    assert set_status(client, admin_headers, second, "open").status_code == 409


def test_customer_cannot_change_status(client, admin_headers, customer_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]
    assert set_status(client, customer_headers, session_id, "open").status_code == 403


# ---------------- sessions: update and delete ----------------
def test_admin_updates_scheduled_session(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]

    response = client.patch(
        f"{URL}/sessions/{session_id}", json={"notes": "Festival rush"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Festival rush"


def test_update_rejects_bad_times_and_past_dates(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]
    path = f"{URL}/sessions/{session_id}"

    assert client.patch(path, json={"end_time": "08:00:00"}, headers=admin_headers).status_code == 400
    past = (today() - timedelta(days=1)).isoformat()
    assert client.patch(path, json={"session_date": past}, headers=admin_headers).status_code == 400


def test_open_session_cannot_be_edited_or_deleted(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]
    set_status(client, admin_headers, session_id, "open")
    path = f"{URL}/sessions/{session_id}"

    assert client.patch(path, json={"notes": "x"}, headers=admin_headers).status_code == 409
    assert client.delete(path, headers=admin_headers).status_code == 409


def test_admin_deletes_scheduled_session(client, admin_headers):
    location_id = make_location(client, admin_headers).json()["id"]
    session_id = make_session(client, admin_headers, location_id).json()["id"]

    assert client.delete(f"{URL}/sessions/{session_id}", headers=admin_headers).status_code == 204
    assert client.get(f"{URL}/sessions", headers=admin_headers).json() == []


# ---------------- nearest ----------------
def test_nearest_orders_by_distance(client, admin_headers):
    near = make_location(client, admin_headers, "Bengaluru Spot", 12.9716, 77.5946).json()["id"]
    far = make_location(client, admin_headers, "Chennai Spot", 13.0827, 80.2707).json()["id"]
    make_session(client, admin_headers, near)
    make_session(client, admin_headers, far)

    result = client.get(f"{URL}/nearest?lat=12.97&lng=77.59").json()
    assert [r["location"]["name"] for r in result] == ["Bengaluru Spot", "Chennai Spot"]
    assert result[0]["distance_km"] < 1


def test_haversine_distance():
    assert haversine_km(12.9, 77.5, 12.9, 77.5) == 0
    assert 280 < haversine_km(12.9716, 77.5946, 13.0827, 80.2707) < 300
