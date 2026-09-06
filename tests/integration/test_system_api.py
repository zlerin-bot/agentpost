from fastapi.testclient import TestClient

from agentpost import __version__


def test_openapi_version_matches_running_server(client: TestClient) -> None:
    assert client.get("/openapi.json").json()["info"]["version"] == __version__


def test_health_does_not_require_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.56"}
    assert response.headers["X-Request-ID"]


def test_ready_checks_database(client: TestClient) -> None:
    response = client.get("/ready", headers={"X-Request-ID": "test-ready-1"})

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "version": "0.1.56"}
    assert response.headers["X-Request-ID"] == "test-ready-1"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "not valid with spaces"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "not valid with spaces"
