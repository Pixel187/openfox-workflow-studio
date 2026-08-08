"""Tests de l'export natif + bundle zip (routes_export.py + ziputil)."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import agent_base
from app.main import app
from app.ziputil import safe_extractall


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    """Client de test avec WS_DIR et AGENT_BASE_DIR temporaires."""
    from app import config

    config.settings.ws_dir = str(tmp_path)
    agent_base.AGENT_BASE_DIR = tmp_path / "agent_base"
    agent_base.seed_if_empty()
    return TestClient(app)


def _workflow(workflow_id: str = "demo") -> dict:
    return {
        "metadata": {
            "id": workflow_id,
            "name": workflow_id,
            "description": "Test",
            "version": "1.0.0",
            "color": "#3b82f6",
        },
        "entryStep": "s1",
        "settings": {"maxIterations": 50},
        "steps": [
            {
                "id": "s1",
                "name": "S",
                "type": "agent",
                "phase": "build",
                "agentId": "builder",
                "prompt": "ok",
                "transitions": [{"goto": "$done"}],
            }
        ],
        "startCondition": {"type": "always"},
    }


def test_export_native_file(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.get("/api/workflows/demo/export")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "demo.workflow.json" in response.headers.get("content-disposition", "")
    data = json.loads(response.content)
    assert data["metadata"]["id"] == "demo"


def test_export_native_404(client: TestClient) -> None:
    response = client.get("/api/workflows/inexistant/export")
    assert response.status_code == 404


def test_export_bundle_contains_workflows_and_agents(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    client.post("/api/workflows", json=_workflow("demo2"))
    response = client.get("/api/export/bundle")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/zip")

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = zf.namelist()
    assert "workflows/demo.workflow.json" in names
    assert "workflows/demo2.workflow.json" in names
    assert "agent_base/planner.json" in names
    assert "agent_base/verifier.json" in names
    assert "manifest.json" in names
    assert "README-export.md" in names


def test_export_bundle_manifest_valid(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.get("/api/export/bundle")
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["schemaVersion"] == "1.0"
    assert manifest["exporter"] == "workflow-studio"
    assert "demo" in manifest["workflow_ids"]
    assert "date" in manifest


def test_export_bundle_zip_integrity(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow())
    response = client.get("/api/export/bundle")
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    assert zf.testzip() is None


def test_safe_extractall_rejects_absolute_path(tmp_path: Path) -> None:
    zf = zipfile.ZipFile(io.BytesIO(), "w")
    zf.writestr("/etc/evil.txt", "x")
    zf.close()
    with pytest.raises(ValueError):
        safe_extractall(zf, tmp_path)


def test_safe_extractall_rejects_dotdot(tmp_path: Path) -> None:
    zf = zipfile.ZipFile(io.BytesIO(), "w")
    zf.writestr("../evil.txt", "x")
    zf.close()
    with pytest.raises(ValueError):
        safe_extractall(zf, tmp_path)


def test_safe_extractall_accepts_normal(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    zf = zipfile.ZipFile(buffer, "w")
    zf.writestr("workflows/demo.workflow.json", "{}")
    zf.close()
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as reopened:
        safe_extractall(reopened, tmp_path)
    assert (tmp_path / "workflows" / "demo.workflow.json").exists()


def test_export_accented_filename(client: TestClient) -> None:
    client.post("/api/workflows", json=_workflow("mots-cles-sujets"))
    response = client.get("/api/workflows/mots-cles-sujets/export")
    assert response.status_code == 200
    assert "mots-cles-sujets.workflow.json" in response.headers.get(
        "content-disposition", ""
    )