from tests.conftest import PREFIX

URL = f"{PREFIX}/products"


def make(client, headers, name="Classic Nankhatai", **extra):
    payload = {"name": name, "price": "120.00", **extra}
    return client.post(URL, json=payload, headers=headers)


def test_public_menu_starts_empty(client):
    response = client.get(URL)
    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_create_product(client, admin_headers):
    response = make(client, admin_headers, category="Biscuits")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Classic Nankhatai"
    assert body["category"] == "biscuits"  # normalised to lower-case
    assert body["is_available"] is True
    assert "updated_at" in body


def test_customer_cannot_create_product(client, customer_headers):
    assert make(client, customer_headers).status_code == 403


def test_anonymous_cannot_create_product(client):
    assert make(client, {}).status_code in (401, 403)


def test_duplicate_name_is_rejected(client, admin_headers):
    assert make(client, admin_headers).status_code == 201
    assert make(client, admin_headers).status_code == 409


def test_invalid_price_is_rejected(client, admin_headers):
    for bad in ("0", "-5"):
        response = client.post(
            URL, json={"name": "Bad Price", "price": bad}, headers=admin_headers
        )
        assert response.status_code == 422


def test_available_only_hides_sold_out(client, admin_headers):
    make(client, admin_headers, "In Stock")
    make(client, admin_headers, "Sold Out", is_available=False)

    names_all = {p["name"] for p in client.get(URL).json()}
    names_available = {p["name"] for p in client.get(f"{URL}?available_only=true").json()}

    assert names_all == {"In Stock", "Sold Out"}
    assert names_available == {"In Stock"}


def test_category_filter(client, admin_headers):
    make(client, admin_headers, "Plain", category="nankhatai")
    make(client, admin_headers, "Salty", category="savoury")
    names = [p["name"] for p in client.get(f"{URL}?category=savoury").json()]
    assert names == ["Salty"]


def test_admin_can_update_product(client, admin_headers):
    product_id = make(client, admin_headers).json()["id"]
    response = client.patch(
        f"{URL}/{product_id}", json={"price": "150.00"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["price"] == "150.00"


def test_customer_cannot_update_product(client, admin_headers, customer_headers):
    product_id = make(client, admin_headers).json()["id"]
    response = client.patch(
        f"{URL}/{product_id}", json={"price": "1.00"}, headers=customer_headers
    )
    assert response.status_code == 403


def test_delete_is_soft(client, admin_headers):
    product_id = make(client, admin_headers).json()["id"]

    assert client.delete(f"{URL}/{product_id}", headers=admin_headers).status_code == 204
    assert client.get(URL).json() == []  # gone from the public menu
    assert client.get(f"{URL}/{product_id}").status_code == 404

    everything = client.get(f"{URL}/admin/all", headers=admin_headers).json()
    assert len(everything) == 1 and everything[0]["is_active"] is False


def test_unknown_product_returns_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"{URL}/{missing}").status_code == 404
