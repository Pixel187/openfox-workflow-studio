"""Tests du point de terminaison de santé GET /api/health."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    """Le endpoint /api/health retourne HTTP 200 avec le payload attendu."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload == {"status": "ok", "app": "workflow-studio"}


def test_health_via_factory() -> None:
    """L'app factory produit une application avec la route de santé."""
    from app import create_app

    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
