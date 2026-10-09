from tests.conftest import PREFIX

USERS = f"{PREFIX}/users"


def test_no_token_is_rejected(client):
    assert client.get(f"{USERS}/admin-check").status_code in (401, 403)


def test_garbage_token_is_rejected(client):
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert client.get(f"{USERS}/admin-check", headers=headers).status_code == 401


def test_admin_can_use_admin_route(client, admin_headers):
    response = client.get(f"{USERS}/admin-check", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_customer_cannot_use_admin_route(client, customer_headers):
    assert client.get(f"{USERS}/admin-check", headers=customer_headers).status_code == 403


def test_customer_can_use_customer_route(client, customer_headers):
    response = client.get(f"{USERS}/customer-check", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "customer"


def test_admin_is_blocked_from_customer_only_route(client, admin_headers):
    assert client.get(f"{USERS}/customer-check", headers=admin_headers).status_code == 403


def test_customer_cannot_list_users(client, customer_headers):
    assert client.get(USERS, headers=customer_headers).status_code == 403


def test_admin_can_list_users(client, admin_headers):
    response = client.get(USERS, headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_deactivated_user_is_locked_out(client, customer_headers):
    from tests.conftest import TestingSession
    from app.modules.users.models import User

    with TestingSession() as db:
        user = db.query(User).filter(User.role == "customer").one()
        user.is_active = False
        db.commit()
    # the token is still valid, but the account is not
    assert client.get(f"{USERS}/me", headers=customer_headers).status_code == 401
