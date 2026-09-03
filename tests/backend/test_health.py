"""Backend health endpoint test."""

from fastapi.testclient import TestClient

from jmcomic_backend.main import create_app


def test_health_check(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"]
    assert data["dataDir"] == str(tmp_path)


def test_get_settings(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["theme"] == "system"
