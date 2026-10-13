import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import PREFIX, TestingSession, _headers_for

REVIEWS = f"{PREFIX}/reviews"
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


def make_product(client, headers, name="Classic Nankhatai") -> str:
    return client.post(
        f"{PREFIX}/products", json={"name": name, "price": "120.00"}, headers=headers
    ).json()["id"]


def buy(client, admin_headers, customer_headers, session_id, product_id, complete=True) -> str:
    """Customer orders the product; admin walks the order to 'completed'."""
    order_id = client.post(
        ORDERS,
        json={"session_id": session_id, "items": [{"product_id": product_id, "quantity": 1}]},
        headers=customer_headers,
    ).json()["id"]
    if complete:
        for step in ("confirmed", "preparing", "ready", "completed"):
            client.patch(
                f"{ORDERS}/{order_id}/status", json={"status": step}, headers=admin_headers
            )
    return order_id


def stocked_product(client, admin_headers, name="Classic Nankhatai"):
    session_id = make_session(client, admin_headers)
    product_id = make_product(client, admin_headers, name)
    client.put(
        f"{PREFIX}/inventory/sessions/{session_id}/products/{product_id}",
        json={"stocked_qty": 100},
        headers=admin_headers,
    )
    return session_id, product_id


def review(client, headers, product_id, rating=5, **extra):
    return client.post(
        REVIEWS, json={"product_id": product_id, "rating": rating, **extra}, headers=headers
    )


def verified_buyer(client, admin_headers, customer_headers, name="Classic Nankhatai"):
    """A product the customer has bought and received."""
    session_id, product_id = stocked_product(client, admin_headers, name)
    buy(client, admin_headers, customer_headers, session_id, product_id)
    return session_id, product_id


# ---------------- who may review ----------------
def test_buyer_can_review_after_completed_order(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)

    response = review(client, customer_headers, pid, 4, comment="  Crisp and fresh  ")
    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == 4
    assert body["comment"] == "Crisp and fresh"  # trimmed
    assert body["product_name"] == "Classic Nankhatai"
    assert body["is_hidden"] is False


def test_cannot_review_without_buying(client, admin_headers, customer_headers):
    pid = make_product(client, admin_headers)
    assert review(client, customer_headers, pid).status_code == 403


def test_cannot_review_before_order_is_completed(client, admin_headers, customer_headers):
    session_id, pid = stocked_product(client, admin_headers)
    buy(client, admin_headers, customer_headers, session_id, pid, complete=False)
    assert review(client, customer_headers, pid).status_code == 403


def test_cancelled_order_does_not_count(client, admin_headers, customer_headers):
    session_id, pid = stocked_product(client, admin_headers)
    order_id = buy(client, admin_headers, customer_headers, session_id, pid, complete=False)
    client.post(f"{ORDERS}/me/{order_id}/cancel", headers=customer_headers)
    assert review(client, customer_headers, pid).status_code == 403


def test_someone_elses_purchase_does_not_count(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    stranger = _headers_for(client, "9000000003", "customer")
    assert review(client, stranger, pid).status_code == 403


def test_anonymous_cannot_review(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    assert review(client, {}, pid).status_code in (401, 403)


def test_unknown_product_is_404(client, customer_headers):
    missing = "00000000-0000-0000-0000-000000000000"
    assert review(client, customer_headers, missing).status_code == 404


# ---------------- validation ----------------
@pytest.mark.parametrize("rating", [0, 6, -1, 100])
def test_rating_must_be_between_1_and_5(client, admin_headers, customer_headers, rating):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    assert review(client, customer_headers, pid, rating).status_code == 422


def test_comment_is_optional_and_length_limited(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    assert review(client, customer_headers, pid, 5, comment="x" * 1001).status_code == 422
    response = review(client, customer_headers, pid, 5)
    assert response.status_code == 201
    assert response.json()["comment"] is None


# ---------------- duplicates ----------------
def test_one_review_per_product(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    assert review(client, customer_headers, pid, 5).status_code == 201
    second = review(client, customer_headers, pid, 1)
    assert second.status_code == 409
    assert "Edit your review" in second.json()["detail"]
    assert len(client.get(f"{REVIEWS}/me", headers=customer_headers).json()) == 1


def test_buying_twice_still_allows_only_one_review(client, admin_headers, customer_headers):
    session_id, pid = stocked_product(client, admin_headers)
    buy(client, admin_headers, customer_headers, session_id, pid)
    buy(client, admin_headers, customer_headers, session_id, pid)
    assert review(client, customer_headers, pid).status_code == 201
    assert review(client, customer_headers, pid).status_code == 409


def test_two_customers_can_review_the_same_product(client, admin_headers, customer_headers):
    session_id, pid = stocked_product(client, admin_headers)
    buy(client, admin_headers, customer_headers, session_id, pid)
    other = _headers_for(client, "9000000003", "customer")
    buy(client, admin_headers, other, session_id, pid)

    assert review(client, customer_headers, pid, 5).status_code == 201
    assert review(client, other, pid, 3).status_code == 201


def test_database_blocks_duplicate_and_bad_ratings(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    review(client, customer_headers, pid)

    with TestingSession() as db:
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO reviews (id, customer_id, product_id, rating) "
                    "SELECT gen_random_uuid(), customer_id, product_id, 3 FROM reviews"
                )
            )
            db.commit()
    with TestingSession() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE reviews SET rating = 9"))
            db.commit()


# ---------------- my reviews: view, edit, delete ----------------
def test_customer_views_only_own_reviews(client, admin_headers, customer_headers):
    session_id, pid = stocked_product(client, admin_headers)
    other = _headers_for(client, "9000000003", "customer")
    buy(client, admin_headers, customer_headers, session_id, pid)
    buy(client, admin_headers, other, session_id, pid)

    mine = review(client, customer_headers, pid, 5).json()["id"]
    review(client, other, pid, 2)

    listed = client.get(f"{REVIEWS}/me", headers=customer_headers).json()
    assert [r["id"] for r in listed] == [mine]
    assert client.get(f"{REVIEWS}/me/{mine}", headers=customer_headers).status_code == 200
    assert client.get(f"{REVIEWS}/me/{mine}", headers=other).status_code == 404  # not theirs


def test_customer_edits_own_review(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid, 3, comment="ok").json()["id"]

    response = client.patch(
        f"{REVIEWS}/me/{rid}", json={"rating": 5, "comment": "Loved it"}, headers=customer_headers
    )
    assert response.status_code == 200
    assert response.json()["rating"] == 5
    assert response.json()["comment"] == "Loved it"


def test_edit_validation(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid, 3).json()["id"]
    path = f"{REVIEWS}/me/{rid}"
    assert client.patch(path, json={"rating": 9}, headers=customer_headers).status_code == 422
    assert client.patch(path, json={"rating": None}, headers=customer_headers).status_code == 400
    assert client.patch(path, json={}, headers=customer_headers).status_code == 400


def test_cannot_edit_or_delete_someone_elses_review(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid, 4).json()["id"]
    stranger = _headers_for(client, "9000000003", "customer")

    edit = client.patch(f"{REVIEWS}/me/{rid}", json={"rating": 1}, headers=stranger)
    assert edit.status_code == 404
    assert client.delete(f"{REVIEWS}/me/{rid}", headers=stranger).status_code == 404
    assert client.get(f"{REVIEWS}/me/{rid}", headers=customer_headers).json()["rating"] == 4


def test_customer_deletes_own_review_and_can_review_again(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid, 2).json()["id"]

    assert client.delete(f"{REVIEWS}/me/{rid}", headers=customer_headers).status_code == 204
    assert client.get(f"{REVIEWS}/me", headers=customer_headers).json() == []
    assert review(client, customer_headers, pid, 5).status_code == 201


# ---------------- public product reviews ----------------
def test_product_reviews_are_public_and_private_details_stay_hidden(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    review(client, customer_headers, pid, 5, comment="Great")

    reviews = client.get(f"{REVIEWS}/product/{pid}").json()  # no login
    assert len(reviews) == 1
    assert reviews[0]["reviewer_name"] == "Test"  # first name only ("Test customer")
    assert "customer_phone" not in reviews[0]
    assert "customer_id" not in reviews[0]
    assert "9000000002" not in str(reviews)


def test_unknown_product_reviews_is_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"{REVIEWS}/product/{missing}").status_code == 404
    assert client.get(f"{REVIEWS}/product/{missing}/summary").status_code == 404


def test_rating_summary(client, admin_headers, customer_headers):
    session_id, pid = stocked_product(client, admin_headers)
    empty = client.get(f"{REVIEWS}/product/{pid}/summary").json()
    assert empty["count"] == 0 and empty["average"] is None

    for index, rating in enumerate((5, 4, 3)):
        who = _headers_for(client, f"900000010{index}", "customer")
        buy(client, admin_headers, who, session_id, pid)
        review(client, who, pid, rating)

    summary = client.get(f"{REVIEWS}/product/{pid}/summary").json()
    assert summary["count"] == 3
    assert summary["average"] == 4.0
    assert summary["stars"] == {"1": 0, "2": 0, "3": 1, "4": 1, "5": 1}


def test_product_review_pagination(client, admin_headers):
    session_id, pid = stocked_product(client, admin_headers)
    for index in range(3):
        who = _headers_for(client, f"900000020{index}", "customer")
        buy(client, admin_headers, who, session_id, pid)
        review(client, who, pid, 4)

    path = f"{REVIEWS}/product/{pid}"
    assert len(client.get(path).json()) == 3
    assert len(client.get(f"{path}?limit=2").json()) == 2
    assert len(client.get(f"{path}?limit=2&offset=2").json()) == 1
    assert client.get(f"{path}?limit=0").status_code == 422


# ---------------- admin moderation ----------------
def test_customer_cannot_use_admin_review_routes(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid).json()["id"]

    assert client.get(f"{REVIEWS}/admin", headers=customer_headers).status_code == 403
    assert client.get(f"{REVIEWS}/admin/{rid}", headers=customer_headers).status_code == 403
    assert client.post(f"{REVIEWS}/admin/{rid}/hide", json={}, headers=customer_headers).status_code == 403
    assert client.post(f"{REVIEWS}/admin/{rid}/restore", headers=customer_headers).status_code == 403
    assert client.delete(f"{REVIEWS}/admin/{rid}", headers=customer_headers).status_code == 403


def test_admin_sees_customer_details_and_filters(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    review(client, customer_headers, pid, 2, comment="Too salty")

    everything = client.get(f"{REVIEWS}/admin", headers=admin_headers).json()
    assert len(everything) == 1
    assert everything[0]["customer_phone"] == "9000000002"
    assert everything[0]["customer_name"] == "Test customer"

    assert len(client.get(f"{REVIEWS}/admin?rating=2", headers=admin_headers).json()) == 1
    assert client.get(f"{REVIEWS}/admin?rating=5", headers=admin_headers).json() == []
    assert len(client.get(f"{REVIEWS}/admin?product_id={pid}", headers=admin_headers).json()) == 1
    assert client.get(f"{REVIEWS}/admin?rating=9", headers=admin_headers).status_code == 422


def test_hidden_review_disappears_from_public_and_ratings(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid, 1, comment="spam spam").json()["id"]

    hidden = client.post(
        f"{REVIEWS}/admin/{rid}/hide", json={"reason": "Spam"}, headers=admin_headers
    )
    assert hidden.status_code == 200
    assert hidden.json()["is_hidden"] is True
    assert hidden.json()["hidden_reason"] == "Spam"

    assert client.get(f"{REVIEWS}/product/{pid}").json() == []
    summary = client.get(f"{REVIEWS}/product/{pid}/summary").json()
    assert summary["count"] == 0 and summary["average"] is None

    # still stored: admin can see it, filter for it, and the author still has it
    assert len(client.get(f"{REVIEWS}/admin?hidden=true", headers=admin_headers).json()) == 1
    assert client.get(f"{REVIEWS}/admin?hidden=false", headers=admin_headers).json() == []
    assert client.get(f"{REVIEWS}/me/{rid}", headers=customer_headers).json()["is_hidden"] is True


def test_admin_can_restore_hidden_review(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid, 4).json()["id"]
    client.post(f"{REVIEWS}/admin/{rid}/hide", json={"reason": "Check"}, headers=admin_headers)

    restored = client.post(f"{REVIEWS}/admin/{rid}/restore", headers=admin_headers)
    assert restored.status_code == 200
    assert restored.json()["is_hidden"] is False
    assert restored.json()["hidden_reason"] is None
    assert len(client.get(f"{REVIEWS}/product/{pid}").json()) == 1


def test_admin_hide_validation(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid).json()["id"]
    long_reason = {"reason": "x" * 301}
    assert client.post(f"{REVIEWS}/admin/{rid}/hide", json=long_reason, headers=admin_headers).status_code == 422
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"{REVIEWS}/admin/{missing}/hide", json={}, headers=admin_headers).status_code == 404


def test_admin_deletes_review_permanently(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    rid = review(client, customer_headers, pid).json()["id"]

    assert client.delete(f"{REVIEWS}/admin/{rid}", headers=admin_headers).status_code == 204
    assert client.get(f"{REVIEWS}/admin/{rid}", headers=admin_headers).status_code == 404
    assert client.delete(f"{REVIEWS}/admin/{rid}", headers=admin_headers).status_code == 404


def test_removed_product_keeps_its_reviews_readable(client, admin_headers, customer_headers):
    _, pid = verified_buyer(client, admin_headers, customer_headers)
    review(client, customer_headers, pid, 5)
    client.delete(f"{PREFIX}/products/{pid}", headers=admin_headers)  # soft delete

    mine = client.get(f"{REVIEWS}/me", headers=customer_headers).json()
    assert mine[0]["product_name"] == "Classic Nankhatai"
    assert client.get(f"{REVIEWS}/product/{pid}").status_code == 404  # product is gone
