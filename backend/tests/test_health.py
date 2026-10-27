from tests.conftest import PREFIX


def test_api_health_reports_app_info(client):
    r = client.get(f"{PREFIX}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert {"app", "version", "environment"} <= set(body)