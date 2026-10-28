import pytest
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.modules.notifications import fcm
from app.modules.notifications.fcm import FcmSender, SendResult, get_push_sender
from app.modules.notifications.models import DeviceToken, Notification
from app.modules.users.models import User

try:
    from tests.conftest import TestingSession
except ImportError:  # tests/ without a package
    from conftest import TestingSession

PREFIX = settings.API_V1_PREFIX
ADMIN, CUSTOMER = "9000000001", "9000000002"
TOK_A, TOK_B = "a" * 30, "b" * 30


class FakeSender:
    def __init__(self, bad=()):
        self.sent = []
        self.bad = set(bad)

    def send(self, token, title, body, data=None):
        self.sent.append((token, title, body))
        if token in self.bad:
            return SendResult(ok=False, invalid_token=True, error="UNREGISTERED")
        return SendResult(ok=True)


def use_sender(sender):
    app.dependency_overrides[get_push_sender] = lambda: sender


def _uid(phone):
    with TestingSession() as db:
        return db.scalar(select(User.id).where(User.phone == phone))


def _add_notification(audience, user_id=None, title="Order ready", body="Pick up now"):
    with TestingSession() as db:
        n = Notification(
            event_type="test_event", audience=audience, user_id=user_id, title=title, body=body
        )
        db.add(n)
        db.commit()
        return n.id


def _state(nid):
    with TestingSession() as db:
        n = db.get(Notification, nid)
        return n.status, n.sent_at


def _token_count():
    with TestingSession() as db:
        return len(db.scalars(select(DeviceToken)).all())


def _register(client, headers, token, platform="android"):
    return client.post(
        f"{PREFIX}/notifications/device-token",
        json={"token": token, "platform": platform},
        headers=headers,
    )


def _dispatch(client, headers):
    return client.post(f"{PREFIX}/notifications/dispatch", headers=headers)


def test_register_requires_login(client):
    r = client.post(f"{PREFIX}/notifications/device-token", json={"token": TOK_A})
    assert r.status_code in (401, 403)


def test_register_is_idempotent(client, customer_headers):
    assert _register(client, customer_headers, TOK_A).status_code == 204
    assert _register(client, customer_headers, TOK_A).status_code == 204
    with TestingSession() as db:
        rows = db.scalars(select(DeviceToken)).all()
    assert len(rows) == 1
    assert rows[0].user_id == _uid(CUSTOMER)


def test_token_moves_to_the_new_account(client, admin_headers, customer_headers):
    _register(client, customer_headers, TOK_A)
    _register(client, admin_headers, TOK_A)
    with TestingSession() as db:
        rows = db.scalars(select(DeviceToken)).all()
    assert len(rows) == 1
    assert rows[0].user_id == _uid(ADMIN)


def test_invalid_registration_input(client, customer_headers):
    assert _register(client, customer_headers, "short").status_code == 422
    assert _register(client, customer_headers, TOK_A, platform="windows").status_code == 422


def test_remove_only_removes_own_token(client, admin_headers, customer_headers):
    _register(client, customer_headers, TOK_A)
    url = f"{PREFIX}/notifications/device-token"
    assert client.delete(url, params={"token": TOK_A}, headers=admin_headers).status_code == 204
    assert _token_count() == 1
    assert client.delete(url, params={"token": TOK_A}, headers=customer_headers).status_code == 204
    assert _token_count() == 0


def test_dispatch_requires_admin(client, customer_headers):
    use_sender(FakeSender())
    assert _dispatch(client, customer_headers).status_code == 403


def test_dispatch_without_configuration_returns_503(client, admin_headers):
    app.dependency_overrides[get_push_sender] = lambda: None
    assert _dispatch(client, admin_headers).status_code == 503


def test_user_notification_reaches_only_that_users_devices(
    client, admin_headers, customer_headers
):
    _register(client, customer_headers, TOK_A)
    _register(client, admin_headers, TOK_B)
    nid = _add_notification("user", _uid(CUSTOMER))
    sender = FakeSender()
    use_sender(sender)
    r = _dispatch(client, admin_headers)
    assert r.status_code == 200
    assert r.json() == {
        "considered": 1, "sent": 1, "failed": 0, "no_devices": 0, "invalid_tokens_removed": 0,
    }
    assert [t for t, _, _ in sender.sent] == [TOK_A]
    status, sent_at = _state(nid)
    assert status == "sent" and sent_at is not None


def test_admin_and_customer_audiences(client, admin_headers, customer_headers):
    _register(client, customer_headers, TOK_A)
    _register(client, admin_headers, TOK_B)
    _add_notification("admins", title="for-admins")
    _add_notification("all_customers", title="for-customers")
    sender = FakeSender()
    use_sender(sender)
    assert _dispatch(client, admin_headers).json()["sent"] == 2
    assert set((t, title) for t, title, _ in sender.sent) == {
        (TOK_B, "for-admins"),
        (TOK_A, "for-customers"),
    }


def test_no_registered_device_marks_failed(client, admin_headers):
    nid = _add_notification("admins")
    use_sender(FakeSender())
    body = _dispatch(client, admin_headers).json()
    assert body["failed"] == 1 and body["no_devices"] == 1 and body["sent"] == 0
    assert _state(nid)[0] == "failed"


def test_invalid_token_is_removed_and_failure_recorded(client, admin_headers, customer_headers):
    _register(client, customer_headers, TOK_A)
    nid = _add_notification("user", _uid(CUSTOMER))
    use_sender(FakeSender(bad={TOK_A}))
    body = _dispatch(client, admin_headers).json()
    assert body["failed"] == 1 and body["invalid_tokens_removed"] == 1
    assert _state(nid)[0] == "failed"
    assert _token_count() == 0


def test_one_bad_device_does_not_block_the_other(client, admin_headers, customer_headers):
    _register(client, customer_headers, TOK_A)
    _register(client, customer_headers, TOK_B)
    nid = _add_notification("user", _uid(CUSTOMER))
    use_sender(FakeSender(bad={TOK_A}))
    body = _dispatch(client, admin_headers).json()
    assert body["sent"] == 1 and body["invalid_tokens_removed"] == 1
    assert _state(nid)[0] == "sent"
    assert _token_count() == 1


def test_second_dispatch_has_nothing_to_send(client, admin_headers, customer_headers):
    _register(client, customer_headers, TOK_A)
    _add_notification("user", _uid(CUSTOMER))
    sender = FakeSender()
    use_sender(sender)
    _dispatch(client, admin_headers)
    again = _dispatch(client, admin_headers).json()
    assert again["considered"] == 0
    assert len(sender.sent) == 1


def test_inactive_users_devices_are_skipped(client, admin_headers, customer_headers):
    _register(client, customer_headers, TOK_A)
    with TestingSession() as db:
        user = db.scalar(select(User).where(User.phone == CUSTOMER))
        user.is_active = False
        db.commit()
    _add_notification("user", _uid(CUSTOMER))
    sender = FakeSender()
    use_sender(sender)
    body = _dispatch(client, admin_headers).json()
    assert body["no_devices"] == 1
    assert sender.sent == []


class _Resp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def _fcm_sender():
    s = FcmSender.__new__(FcmSender)
    s._url = "https://fcm.example/send"
    s._access_token = lambda: "access"
    return s


def test_fcm_sender_success(monkeypatch):
    monkeypatch.setattr(fcm.requests, "post", lambda *a, **k: _Resp(200, "{}"))
    assert _fcm_sender().send("t" * 30, "T", "B").ok is True


def test_fcm_sender_unregistered_token_is_invalid(monkeypatch):
    monkeypatch.setattr(
        fcm.requests, "post", lambda *a, **k: _Resp(404, '{"error": "UNREGISTERED"}')
    )
    result = _fcm_sender().send("t" * 30, "T", "B")
    assert result.ok is False and result.invalid_token is True


def test_fcm_sender_network_error_is_not_an_invalid_token(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(fcm.requests, "post", boom)
    result = _fcm_sender().send("t" * 30, "T", "B")
    assert result.ok is False and result.invalid_token is False