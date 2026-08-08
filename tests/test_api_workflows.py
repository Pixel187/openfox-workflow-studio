"""Tests d'intégration de l'API REST CRUD workflows (routes_workflows.py)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    """Client de test avec WS_DIR temporaire."""
    from app import config

    config.settings.ws_dir = str(tmp_path)
    client = TestClient(app)
    client.app.state.ws_dir = tmp_path
    return client


def _workflow(workflow_id: str = "demo", name: str = "Demo") -> dict:
    return {
        "metadata": {
            "id": workflow_id,
            "name": name,
            "description": "Workflow de test",
            "version": "1.0.0",
            "color": "#3b82f6",
        },
        "entryStep": "s1",
        "settings": {"maxIterations": 50},
        "steps": [
            {
                "id": "s1",
                "name": "Step 1",
                "type": "agent",
                "phase": "build",
                "agentId": "builder",
                "prompt": "Fais le travail",
                "transitions": [{"goto": "$done"}],
            }
        ],
        "startCondition": {"type": "always"},
    }


def _etag(response) -> str:
    return response.headers["ETag"]


def test_list_empty(client: TestClient) -> None:
    response = client.get("/api/workflows")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get(client: TestClient) -> None:
    response = client.post("/api/workflows", json=_workflow())
    assert response.status_code == 201
    assert "ETag" in response.headers

    listing = client.get("/api/workflows")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    assert items[0]["id"] == "demo"
    assert items[0]["stepCount"] == 1

    detail = client.get("/api/workflows/demo")
    assert detail.status_code == 200
    assert detail.json()["metadata"]["id"] == "demo"


def test_create_duplicate_409(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.post("/api/workflows", json=_workflow())
    assert response.status_code == 409


def test_create_slugifies_name(client: TestClient) -> None:
    wf = _workflow()
    wf["metadata"].pop("id")
    wf["metadata"]["name"] = "Mon Workflow Été"
    response = client.post("/api/workflows", json=wf)
    assert response.status_code == 201
    assert response.json()["metadata"]["id"] == "mon-workflow-ete"


def test_put_requires_if_match(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.put("/api/workflows/demo", json=_workflow())
    assert response.status_code == 412


def test_put_with_valid_etag(client: TestClient) -> None:
    created = client.post("/api/workflows", json=_workflow())
    etag = _etag(created)
    wf = _workflow()
    wf["metadata"]["description"] = "Modifié"
    response = client.put(
        "/api/workflows/demo", json=wf, headers={"If-Match": etag}
    )
    assert response.status_code == 200
    assert response.json()["metadata"]["description"] == "Modifié"


def test_put_with_stale_etag_409(client: TestClient) -> None:
    created = client.post("/api/workflows", json=_workflow())
    etag = _etag(created)
    # Modification externe : on réécrit le fichier directement
    path = client.app.state.ws_dir / "demo.workflow.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["metadata"]["description"] = "Externe"
    path.write_text(json.dumps(data), encoding="utf-8")
    wf = _workflow()
    response = client.put(
        "/api/workflows/demo", json=wf, headers={"If-Match": etag}
    )
    assert response.status_code == 409


def test_put_mismatched_id_422(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    wf = _workflow(workflow_id="autre")
    response = client.put(
        "/api/workflows/demo", json=wf, headers={"If-Match": _etag(client.get("/api/workflows/demo"))}
    )
    assert response.status_code == 422


def test_delete_requires_if_match(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.delete("/api/workflows/demo")
    assert response.status_code == 412


def test_delete_with_etag(client: TestClient) -> None:
    created = client.post("/api/workflows", json=_workflow())
    response = client.delete(
        "/api/workflows/demo", headers={"If-Match": _etag(created)}
    )
    assert response.status_code == 204
    assert client.get("/api/workflows/demo").status_code == 404


def test_validate_endpoint(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.post("/api/workflows/demo/validate")
    assert response.status_code == 200
    payload = response.json()
    assert "valid" in payload
    assert "errors" in payload
    assert "warnings" in payload


def test_layout_get_404_when_absent(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.get("/api/workflows/demo/layout")
    assert response.status_code == 404


def test_layout_put_and_get(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    layout = {"nodes": [{"id": "s1", "position": {"x": 10, "y": 20}}]}
    put = client.put("/api/workflows/demo/layout", json=layout)
    assert put.status_code == 200
    get = client.get("/api/workflows/demo/layout")
    assert get.status_code == 200
    assert get.json() == layout


def test_layout_path_traversal_rejected(client: TestClient) -> None:
    response = client.get("/api/workflows/..%5Cevil/layout")
    assert response.status_code in (404, 422)