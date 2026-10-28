from app.core.config import settings

PREFIX = settings.API_V1_PREFIX
PHONE = "9111111111"
PASSWORD = "password123"


def _register(client, **over):
    body = {"name": "Asha Rao", "phone": PHONE, "password": PASSWORD}
    body.update(over)
    return client.post(f"{PREFIX}/auth/register", json=body)


def _login(client, phone=PHONE, password=PASSWORD):
    return client.post(
        f"{PREFIX}/auth/login", json={"phone": phone, "password": password}
    )


def test_register_creates_user_without_password_fields(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["phone"] == PHONE
    assert "password" not in body and "password_hash" not in body


def test_register_cannot_choose_admin_role(client):
    r = _register(client, role="admin")
    assert r.status_code == 201
    assert r.json().get("role") != "admin"


def test_register_duplicate_phone_conflicts(client):
    _register(client)
    r = _register(client, name="Other Person")
    assert r.status_code == 409
    assert r.json()["detail"] == "Phone already registered"


def test_register_duplicate_email_conflicts(client):
    _register(client, email="a@example.com")
    r = _register(client, phone="9222222222", email="a@example.com")
    assert r.status_code == 409
    assert r.json()["detail"] == "Email already registered"


def test_register_validation_errors(client):
    assert _register(client, password="short").status_code == 422
    assert _register(client, phone="123").status_code == 422
    assert _register(client, email="not-an-email").status_code == 422


def test_login_returns_both_tokens(client):
    _register(client)
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_login_wrong_password_and_unknown_phone_look_the_same(client):
    _register(client)
    wrong = _login(client, password="wrong-password")
    unknown = _login(client, phone="9333333333")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Invalid phone or password"


def test_refresh_rotates_and_old_token_is_rejected(client):
    _register(client)
    first = _login(client).json()
    r = client.post(f"{PREFIX}/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200
    second = r.json()
    assert second["refresh_token"] != first["refresh_token"]
    reuse = client.post(f"{PREFIX}/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reuse.status_code == 401
    assert reuse.json()["detail"] == "Invalid or expired refresh token"


def test_refresh_with_garbage_token_is_rejected(client):
    r = client.post(f"{PREFIX}/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


def test_logout_revokes_refresh_token(client):
    _register(client)
    tokens = _login(client).json()
    out = client.post(f"{PREFIX}/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204
    r = client.post(f"{PREFIX}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401