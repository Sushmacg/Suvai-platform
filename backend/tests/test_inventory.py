import threading
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.modules.inventory.service import release_stock, reserve_stock
from tests.conftest import PREFIX, TestingSession

INV = f"{PREFIX}/inventory"
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


def make_product(client, headers, name="Classic Nankhatai") -> str:
    return client.post(
        f"{PREFIX}/products", json={"name": name, "price": "120.00"}, headers=headers
    ).json()["id"]


def put_stock(client, headers, session_id, product_id, qty, **extra):
    return client.put(
        f"{INV}/sessions/{session_id}/products/{product_id}",
        json={"stocked_qty": qty, **extra},
        headers=headers,
    )


def admin_row(client, headers, session_id, product_id):
    rows = client.get(f"{INV}/sessions/{session_id}/admin", headers=headers).json()
    return next(r for r in rows if r["product_id"] == product_id)


def reserve(session_id, items):
    """Reserve and commit, the way the Orders module will."""
    with TestingSession() as db:
        reserve_stock(db, uuid.UUID(session_id), [(uuid.UUID(p), q) for p, q in items])
        db.commit()


# ---------------- admin sets stock ----------------
def test_admin_sets_stock_and_customer_sees_availability(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)

    response = put_stock(client, admin_headers, sid, pid, 40, min_stock=5)
    assert response.status_code == 200
    body = response.json()
    assert body["stocked_qty"] == 40
    assert body["available_qty"] == 40
    assert body["min_stock"] == 5

    public = client.get(f"{INV}/sessions/{sid}").json()
    assert public[0]["product_name"] == "Classic Nankhatai"
    assert public[0]["available_qty"] == 40
    assert public[0]["in_stock"] is True
    assert "sold_qty" not in public[0]  # internal numbers stay private


def test_setting_stock_again_updates_the_same_row(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 40)
    put_stock(client, admin_headers, sid, pid, 55)

    rows = client.get(f"{INV}/sessions/{sid}/admin", headers=admin_headers).json()
    assert len(rows) == 1
    assert rows[0]["stocked_qty"] == 55


def test_customer_cannot_modify_inventory(client, admin_headers, customer_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)

    assert put_stock(client, customer_headers, sid, pid, 999).status_code == 403
    waste = client.post(
        f"{INV}/sessions/{sid}/products/{pid}/waste",
        json={"quantity": 1},
        headers=customer_headers,
    )
    assert waste.status_code == 403
    assert client.get(f"{INV}/sessions/{sid}/admin", headers=customer_headers).status_code == 403
    assert admin_row(client, admin_headers, sid, pid)["stocked_qty"] == 10


def test_invalid_quantities_rejected(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    assert put_stock(client, admin_headers, sid, pid, -1).status_code == 422
    assert put_stock(client, admin_headers, sid, pid, 10, min_stock=-1).status_code == 422


def test_unknown_session_or_product_is_404(client, admin_headers):
    missing = "00000000-0000-0000-0000-000000000000"
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    assert put_stock(client, admin_headers, missing, pid, 5).status_code == 404
    assert put_stock(client, admin_headers, sid, missing, 5).status_code == 404
    assert client.get(f"{INV}/sessions/{missing}").status_code == 404


def test_inactive_product_cannot_be_stocked(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    client.delete(f"{PREFIX}/products/{pid}", headers=admin_headers)
    assert put_stock(client, admin_headers, sid, pid, 5).status_code == 404


def test_cancelled_session_stock_is_locked(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    client.patch(
        f"{PREFIX}/stalls/sessions/{sid}/status",
        json={"status": "cancelled"},
        headers=admin_headers,
    )
    assert put_stock(client, admin_headers, sid, pid, 5).status_code == 409


# ---------------- reserving stock (what Orders will call) ----------------
def test_reserve_reduces_available(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)

    reserve(sid, [(pid, 3)])

    row = admin_row(client, admin_headers, sid, pid)
    assert row["sold_qty"] == 3
    assert row["available_qty"] == 7


def test_cannot_reserve_more_than_available(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 5)

    with pytest.raises(HTTPException) as error:
        reserve(sid, [(pid, 6)])
    assert error.value.status_code == 409
    assert "Only 5 left" in error.value.detail
    assert admin_row(client, admin_headers, sid, pid)["sold_qty"] == 0


def test_can_sell_exactly_the_last_item_and_then_no_more(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 2)

    reserve(sid, [(pid, 2)])
    assert admin_row(client, admin_headers, sid, pid)["available_qty"] == 0
    assert client.get(f"{INV}/sessions/{sid}").json()[0]["in_stock"] is False

    with pytest.raises(HTTPException):
        reserve(sid, [(pid, 1)])


def test_duplicate_items_are_combined_before_checking(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 3)

    with pytest.raises(HTTPException) as error:
        reserve(sid, [(pid, 2), (pid, 2)])  # 4 in total, only 3 available
    assert error.value.status_code == 409


def test_unstocked_product_cannot_be_reserved(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    with pytest.raises(HTTPException) as error:
        reserve(sid, [(pid, 1)])
    assert "not stocked" in error.value.detail


def test_zero_or_negative_quantity_rejected(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 5)
    for bad in (0, -2):
        with pytest.raises(HTTPException) as error:
            reserve(sid, [(pid, bad)])
        assert error.value.status_code == 400


def test_multi_item_order_is_all_or_nothing(client, admin_headers):
    sid = make_session(client, admin_headers)
    first = make_product(client, admin_headers, "Plain")
    second = make_product(client, admin_headers, "Salty")
    put_stock(client, admin_headers, sid, first, 10)
    put_stock(client, admin_headers, sid, second, 1)

    with TestingSession() as db:
        with pytest.raises(HTTPException):
            reserve_stock(
                db,
                uuid.UUID(sid),
                [(uuid.UUID(first), 2), (uuid.UUID(second), 5)],  # the second fails
            )
        db.rollback()  # what the Orders module does on any error

    assert admin_row(client, admin_headers, sid, first)["sold_qty"] == 0
    assert admin_row(client, admin_headers, sid, second)["sold_qty"] == 0


def test_closed_session_cannot_be_reserved(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 5)
    for new_status in ("open", "closed"):
        client.patch(
            f"{PREFIX}/stalls/sessions/{sid}/status",
            json={"status": new_status},
            headers=admin_headers,
        )
    with pytest.raises(HTTPException) as error:
        reserve(sid, [(pid, 1)])
    assert error.value.status_code == 409


def test_concurrent_orders_never_oversell(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 5)

    outcomes = []

    def buy_one():
        with TestingSession() as db:
            try:
                reserve_stock(db, uuid.UUID(sid), [(uuid.UUID(pid), 1)])
                db.commit()
                outcomes.append(True)
            except HTTPException:
                db.rollback()
                outcomes.append(False)

    threads = [threading.Thread(target=buy_one) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(outcomes) == 5  # exactly 5 succeed, 7 are refused
    row = admin_row(client, admin_headers, sid, pid)
    assert row["sold_qty"] == 5
    assert row["available_qty"] == 0


# ---------------- releasing stock (cancelled orders) ----------------
def test_release_gives_stock_back(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)
    reserve(sid, [(pid, 4)])

    with TestingSession() as db:
        release_stock(db, uuid.UUID(sid), [(uuid.UUID(pid), 3)])
        db.commit()

    row = admin_row(client, admin_headers, sid, pid)
    assert row["sold_qty"] == 1
    assert row["available_qty"] == 9


def test_cannot_release_more_than_was_sold(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)
    reserve(sid, [(pid, 2)])

    with TestingSession() as db:
        with pytest.raises(HTTPException) as error:
            release_stock(db, uuid.UUID(sid), [(uuid.UUID(pid), 5)])
        assert error.value.status_code == 409


# ---------------- the stock rules at the admin level ----------------
def test_stock_cannot_be_lowered_below_what_is_sold(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)
    reserve(sid, [(pid, 6)])

    assert put_stock(client, admin_headers, sid, pid, 5).status_code == 400
    assert put_stock(client, admin_headers, sid, pid, 6).status_code == 200


def test_waste_reduces_available_and_cannot_exceed_it(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)
    reserve(sid, [(pid, 4)])
    url = f"{INV}/sessions/{sid}/products/{pid}/waste"

    assert client.post(url, json={"quantity": 7}, headers=admin_headers).status_code == 409
    response = client.post(url, json={"quantity": 6}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["wasted_qty"] == 6
    assert response.json()["available_qty"] == 0


def test_waste_can_be_recorded_after_the_session_closes(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)
    for new_status in ("open", "closed"):
        client.patch(
            f"{PREFIX}/stalls/sessions/{sid}/status",
            json={"status": new_status},
            headers=admin_headers,
        )
    response = client.post(
        f"{INV}/sessions/{sid}/products/{pid}/waste",
        json={"quantity": 3},
        headers=admin_headers,
    )
    assert response.status_code == 200
    # but the stock itself is frozen once closed
    assert put_stock(client, admin_headers, sid, pid, 50).status_code == 409


def test_low_stock_flag_and_filter(client, admin_headers):
    sid = make_session(client, admin_headers)
    low = make_product(client, admin_headers, "Running Low")
    fine = make_product(client, admin_headers, "Plenty")
    put_stock(client, admin_headers, sid, low, 10, min_stock=5)
    put_stock(client, admin_headers, sid, fine, 50, min_stock=5)
    reserve(sid, [(low, 6)])  # 4 left, at or below the minimum of 5

    rows = client.get(f"{INV}/sessions/{sid}/admin?low_stock_only=true", headers=admin_headers).json()
    assert [r["product_name"] for r in rows] == ["Running Low"]
    assert rows[0]["is_low_stock"] is True


def test_sold_out_flag_hides_product_from_stock_even_with_quantity(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 10)
    client.patch(f"{PREFIX}/products/{pid}", json={"is_available": False}, headers=admin_headers)

    item = client.get(f"{INV}/sessions/{sid}").json()[0]
    assert item["available_qty"] == 10
    assert item["in_stock"] is False


# ---------------- the database itself refuses negative stock ----------------
def test_database_constraint_blocks_negative_stock(client, admin_headers):
    sid = make_session(client, admin_headers)
    pid = make_product(client, admin_headers)
    put_stock(client, admin_headers, sid, pid, 5)

    with TestingSession() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE session_stock SET sold_qty = stocked_qty + 1"))
            db.commit()
