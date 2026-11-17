import io

import pytest

from app.core.config import settings
from app.modules.products import images as image_service
from tests.conftest import PREFIX

URL = f"{PREFIX}/products"
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 64


@pytest.fixture(autouse=True)
def media_dir(tmp_path, monkeypatch):
    # Uploaded files go to a temp folder, never into the real uploads folder.
    monkeypatch.setattr(settings, "MEDIA_DIR", str(tmp_path))
    return tmp_path / "products"


def new_product(client, headers, name="Classic Nankhatai", **extra):
    response = client.post(URL, json={"name": name, "price": "120.00", **extra}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def upload(client, headers, product_id, *blobs):
    files = [("files", (f"photo{i}.jpg", io.BytesIO(b), "image/jpeg")) for i, b in enumerate(blobs)]
    return client.post(f"{URL}/{product_id}/images", files=files, headers=headers)


def stored(folder):
    return sorted(folder.glob("*")) if folder.exists() else []


def test_upload_sets_cover_and_saves_files(client, admin_headers, media_dir):
    pid = new_product(client, admin_headers)
    response = upload(client, admin_headers, pid, JPEG, PNG, WEBP)
    assert response.status_code == 201
    body = response.json()
    assert [i["position"] for i in body["images"]] == [0, 1, 2]
    assert body["image_url"] == body["images"][0]["url"]
    assert body["image_url"].startswith("/media/products/")
    assert {p.suffix for p in stored(media_dir)} == {".jpg", ".png", ".webp"}


def test_public_product_includes_images(client, admin_headers):
    pid = new_product(client, admin_headers)
    upload(client, admin_headers, pid, JPEG)
    body = client.get(f"{URL}/{pid}").json()
    assert len(body["images"]) == 1
    assert body["image_url"] == body["images"][0]["url"]


def test_upload_replaces_a_pasted_url_as_cover(client, admin_headers):
    pid = new_product(client, admin_headers, image_url="https://example.com/x.jpg")
    body = upload(client, admin_headers, pid, JPEG).json()
    assert body["image_url"] == body["images"][0]["url"]


def test_rejects_files_that_are_not_images(client, admin_headers, media_dir):
    pid = new_product(client, admin_headers)
    assert upload(client, admin_headers, pid, b"definitely not an image").status_code == 415
    assert stored(media_dir) == []


def test_invalid_file_rolls_back_the_whole_batch(client, admin_headers, media_dir):
    pid = new_product(client, admin_headers)
    assert upload(client, admin_headers, pid, JPEG, b"nope").status_code == 415
    assert stored(media_dir) == []
    assert client.get(f"{URL}/{pid}").json()["images"] == []


def test_rejects_oversized_image(client, admin_headers, media_dir, monkeypatch):
    monkeypatch.setattr(image_service, "MAX_BYTES", 100)
    pid = new_product(client, admin_headers)
    assert upload(client, admin_headers, pid, JPEG + b"0" * 200).status_code == 413
    assert stored(media_dir) == []


def test_limit_per_product(client, admin_headers, monkeypatch):
    monkeypatch.setattr(image_service, "MAX_IMAGES", 2)
    pid = new_product(client, admin_headers)
    assert upload(client, admin_headers, pid, JPEG, JPEG).status_code == 201
    assert upload(client, admin_headers, pid, JPEG).status_code == 422
    assert len(client.get(f"{URL}/{pid}").json()["images"]) == 2


def test_make_cover(client, admin_headers):
    pid = new_product(client, admin_headers)
    second = upload(client, admin_headers, pid, JPEG, PNG).json()["images"][1]
    response = client.put(f"{URL}/{pid}/images/{second['id']}/cover", headers=admin_headers)
    assert response.status_code == 200
    out = response.json()
    assert out["images"][0]["id"] == second["id"]
    assert out["image_url"] == second["url"]


def test_remove_image_moves_cover_and_deletes_file(client, admin_headers, media_dir):
    pid = new_product(client, admin_headers)
    first, second = upload(client, admin_headers, pid, JPEG, PNG).json()["images"]
    response = client.delete(f"{URL}/{pid}/images/{first['id']}", headers=admin_headers)
    assert response.status_code == 200
    out = response.json()
    assert [i["id"] for i in out["images"]] == [second["id"]]
    assert out["image_url"] == second["url"]
    assert len(stored(media_dir)) == 1


def test_removing_the_last_image_clears_the_cover(client, admin_headers, media_dir):
    pid = new_product(client, admin_headers)
    only = upload(client, admin_headers, pid, JPEG).json()["images"][0]
    out = client.delete(f"{URL}/{pid}/images/{only['id']}", headers=admin_headers).json()
    assert out["images"] == []
    assert out["image_url"] is None
    assert stored(media_dir) == []


def test_image_of_another_product_is_404(client, admin_headers):
    a = new_product(client, admin_headers)
    b = new_product(client, admin_headers, "Elaichi Nankhatai")
    image = upload(client, admin_headers, a, JPEG).json()["images"][0]
    assert client.delete(f"{URL}/{b}/images/{image['id']}", headers=admin_headers).status_code == 404


def test_unknown_product_is_404(client, admin_headers):
    assert upload(client, admin_headers, "00000000-0000-0000-0000-000000000000", JPEG).status_code == 404


def test_only_admin_can_upload(client, admin_headers, customer_headers):
    pid = new_product(client, admin_headers)
    assert upload(client, customer_headers, pid, JPEG).status_code == 403
    assert upload(client, {}, pid, JPEG).status_code in (401, 403)