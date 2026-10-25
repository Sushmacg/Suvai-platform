from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import PREFIX, TestingSession

EXPENSES = f"{PREFIX}/expenses"
IST = ZoneInfo("Asia/Kolkata")


def today():
    return datetime.now(IST).date()


def add(client, headers, amount="450.50", category="ingredients", **extra):
    return client.post(
        EXPENSES,
        json={"amount": amount, "category": category, **extra},
        headers=headers,
    )


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
            "session_date": today().isoformat(),
            "start_time": "09:00:00",
            "end_time": "23:59:00",
        },
        headers=headers,
    ).json()["id"]


# ---------------- creating ----------------
def test_admin_creates_expense(client, admin_headers):
    response = add(client, admin_headers, description="  Flour and ghee  ")
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["amount"]) == Decimal("450.50")
    assert body["category"] == "ingredients"
    assert body["description"] == "Flour and ghee"  # trimmed
    assert body["expense_date"] == today().isoformat()  # defaults to today
    assert body["created_by"] is not None
    assert "created_at" in body and "updated_at" in body


def test_expense_with_explicit_past_date(client, admin_headers):
    day = (today() - timedelta(days=3)).isoformat()
    response = add(client, admin_headers, expense_date=day)
    assert response.status_code == 201
    assert response.json()["expense_date"] == day


def test_future_date_rejected(client, admin_headers):
    tomorrow = (today() + timedelta(days=1)).isoformat()
    assert add(client, admin_headers, expense_date=tomorrow).status_code == 400


@pytest.mark.parametrize("amount", ["0", "-10", "-0.01"])
def test_non_positive_amount_rejected(client, admin_headers, amount):
    assert add(client, admin_headers, amount=amount).status_code == 422


def test_amount_with_too_many_decimals_rejected(client, admin_headers):
    assert add(client, admin_headers, amount="10.999").status_code == 422


def test_unknown_category_rejected(client, admin_headers):
    assert add(client, admin_headers, category="holiday").status_code == 422


def test_missing_required_fields_rejected(client, admin_headers):
    assert client.post(EXPENSES, json={"category": "fuel"}, headers=admin_headers).status_code == 422
    assert client.post(EXPENSES, json={"amount": "5"}, headers=admin_headers).status_code == 422


def test_overlong_description_rejected(client, admin_headers):
    assert add(client, admin_headers, description="x" * 501).status_code == 422


# ---------------- admin-only ----------------
def test_customer_has_no_access_at_all(client, admin_headers, customer_headers):
    expense_id = add(client, admin_headers).json()["id"]
    assert add(client, customer_headers).status_code == 403
    assert client.get(EXPENSES, headers=customer_headers).status_code == 403
    assert client.get(f"{EXPENSES}/{expense_id}", headers=customer_headers).status_code == 403
    assert client.get(f"{EXPENSES}/summary", headers=customer_headers).status_code == 403
    patch = client.patch(f"{EXPENSES}/{expense_id}", json={"amount": "1"}, headers=customer_headers)
    assert patch.status_code == 403
    assert client.delete(f"{EXPENSES}/{expense_id}", headers=customer_headers).status_code == 403
    # nothing changed
    assert Decimal(client.get(f"{EXPENSES}/{expense_id}", headers=admin_headers).json()["amount"]) == Decimal("450.50")


def test_anonymous_has_no_access(client):
    assert client.get(EXPENSES).status_code in (401, 403)
    assert client.post(EXPENSES, json={"amount": "5", "category": "fuel"}).status_code in (401, 403)


# ---------------- reading ----------------
def test_get_one_and_unknown_id(client, admin_headers):
    expense_id = add(client, admin_headers).json()["id"]
    assert client.get(f"{EXPENSES}/{expense_id}", headers=admin_headers).status_code == 200
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"{EXPENSES}/{missing}", headers=admin_headers).status_code == 404


def test_list_filters(client, admin_headers):
    add(client, admin_headers, "100.00", "ingredients", expense_date=(today() - timedelta(days=10)).isoformat())
    add(client, admin_headers, "200.00", "fuel", expense_date=(today() - timedelta(days=2)).isoformat())
    add(client, admin_headers, "300.00", "fuel")

    assert len(client.get(EXPENSES, headers=admin_headers).json()) == 3

    fuel = client.get(f"{EXPENSES}?category=fuel", headers=admin_headers).json()
    assert {Decimal(e["amount"]) for e in fuel} == {Decimal("200.00"), Decimal("300.00")}

    since = (today() - timedelta(days=5)).isoformat()
    recent = client.get(f"{EXPENSES}?start={since}", headers=admin_headers).json()
    assert len(recent) == 2

    window = client.get(
        f"{EXPENSES}?start={(today() - timedelta(days=12)).isoformat()}&end={(today() - timedelta(days=5)).isoformat()}",
        headers=admin_headers,
    ).json()
    assert [Decimal(e["amount"]) for e in window] == [Decimal("100.00")]

    bad_range = client.get(
        f"{EXPENSES}?start={today().isoformat()}&end={(today() - timedelta(days=1)).isoformat()}",
        headers=admin_headers,
    )
    assert bad_range.status_code == 400
    assert client.get(f"{EXPENSES}?category=bogus", headers=admin_headers).status_code == 422


def test_newest_first_and_pagination(client, admin_headers):
    for offset in (3, 2, 1):
        add(client, admin_headers, str(offset * 10), expense_date=(today() - timedelta(days=offset)).isoformat())

    dates = [e["expense_date"] for e in client.get(EXPENSES, headers=admin_headers).json()]
    assert dates == sorted(dates, reverse=True)

    assert len(client.get(f"{EXPENSES}?limit=2", headers=admin_headers).json()) == 2
    assert len(client.get(f"{EXPENSES}?limit=2&offset=2", headers=admin_headers).json()) == 1
    assert client.get(f"{EXPENSES}?limit=0", headers=admin_headers).status_code == 422
    assert client.get(f"{EXPENSES}?limit=101", headers=admin_headers).status_code == 422


# ---------------- updating ----------------
def test_admin_updates_expense(client, admin_headers):
    expense_id = add(client, admin_headers).json()["id"]
    response = client.patch(
        f"{EXPENSES}/{expense_id}",
        json={"amount": "500.00", "category": "packaging"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["amount"]) == Decimal("500.00")
    assert body["category"] == "packaging"
    assert body["description"] is None or isinstance(body["description"], str)


def test_update_validation(client, admin_headers):
    expense_id = add(client, admin_headers).json()["id"]
    path = f"{EXPENSES}/{expense_id}"
    assert client.patch(path, json={"amount": "0"}, headers=admin_headers).status_code == 422
    assert client.patch(path, json={"category": "bogus"}, headers=admin_headers).status_code == 422
    assert client.patch(path, json={"amount": None}, headers=admin_headers).status_code == 400
    future = (today() + timedelta(days=1)).isoformat()
    assert client.patch(path, json={"expense_date": future}, headers=admin_headers).status_code == 400


def test_description_can_be_cleared(client, admin_headers):
    expense_id = add(client, admin_headers, description="to be removed").json()["id"]
    response = client.patch(f"{EXPENSES}/{expense_id}", json={"description": None}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["description"] is None


def test_update_unknown_id_is_404(client, admin_headers):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.patch(f"{EXPENSES}/{missing}", json={"amount": "5"}, headers=admin_headers).status_code == 404


# ---------------- deleting ----------------
def test_admin_deletes_expense(client, admin_headers):
    expense_id = add(client, admin_headers).json()["id"]
    assert client.delete(f"{EXPENSES}/{expense_id}", headers=admin_headers).status_code == 204
    assert client.get(f"{EXPENSES}/{expense_id}", headers=admin_headers).status_code == 404
    assert client.delete(f"{EXPENSES}/{expense_id}", headers=admin_headers).status_code == 404


# ---------------- stall session link ----------------
def test_expense_can_be_linked_to_a_session(client, admin_headers):
    sid = make_session(client, admin_headers)
    response = add(client, admin_headers, "250.00", "fuel", session_id=sid)
    assert response.status_code == 201
    assert response.json()["session_id"] == sid

    linked = client.get(f"{EXPENSES}?session_id={sid}", headers=admin_headers).json()
    assert len(linked) == 1


def test_unknown_session_rejected(client, admin_headers):
    missing = "00000000-0000-0000-0000-000000000000"
    assert add(client, admin_headers, session_id=missing).status_code == 404


def test_expense_survives_deleting_its_session(client, admin_headers):
    sid = make_session(client, admin_headers)
    expense_id = add(client, admin_headers, session_id=sid).json()["id"]

    assert client.delete(f"{PREFIX}/stalls/sessions/{sid}", headers=admin_headers).status_code == 204

    body = client.get(f"{EXPENSES}/{expense_id}", headers=admin_headers).json()
    assert body["session_id"] is None  # unlinked, not deleted


def test_session_can_be_unlinked(client, admin_headers):
    sid = make_session(client, admin_headers)
    expense_id = add(client, admin_headers, session_id=sid).json()["id"]
    response = client.patch(f"{EXPENSES}/{expense_id}", json={"session_id": None}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["session_id"] is None


# ---------------- summary ----------------
def test_summary_totals(client, admin_headers):
    add(client, admin_headers, "100.25", "ingredients")
    add(client, admin_headers, "50.00", "ingredients")
    add(client, admin_headers, "200.00", "fuel")

    body = client.get(f"{EXPENSES}/summary", headers=admin_headers).json()
    assert Decimal(body["total"]) == Decimal("350.25")
    assert body["count"] == 3
    assert Decimal(body["by_category"]["ingredients"]) == Decimal("150.25")
    assert Decimal(body["by_category"]["fuel"]) == Decimal("200.00")


def test_summary_respects_filters_and_handles_empty(client, admin_headers):
    empty = client.get(f"{EXPENSES}/summary", headers=admin_headers).json()
    assert Decimal(empty["total"]) == 0 and empty["count"] == 0 and empty["by_category"] == {}

    add(client, admin_headers, "100.00", "fuel", expense_date=(today() - timedelta(days=9)).isoformat())
    add(client, admin_headers, "40.00", "fuel")
    since = (today() - timedelta(days=3)).isoformat()
    body = client.get(f"{EXPENSES}/summary?start={since}", headers=admin_headers).json()
    assert Decimal(body["total"]) == Decimal("40.00")


# ---------------- database rules ----------------
def test_database_rejects_bad_rows(client, admin_headers):
    add(client, admin_headers)
    with TestingSession() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE expenses SET amount = 0"))
            db.commit()
    with TestingSession() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE expenses SET category = 'bogus'"))
            db.commit()