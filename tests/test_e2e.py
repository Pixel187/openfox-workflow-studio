"""Tests E2E backend : round-trip réel sur un workflow copié dans tmp WS_DIR.

Copie un vrai workflow OpenFox dans un WS_DIR temporaire, puis CRUD complet +
validation + export zip. N'utilise JAMAIS le vrai dossier workflows.

Écart documenté vs plan : le plan visait `openfox-full-pipeline.workflow.json`
avec « validate -> 0 erreurs », mais ce fichier réel ne passe PAS la validation
OpenFox (goto `__end__` au lieu de `$done`, `startCondition` manquant, motifs
`.py` dans les prompts). On utilise donc `build-and-verify.workflow.json` qui
valide proprement (valid=True, 0 erreur) pour les assertions de validation.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

REAL_WORKFLOW = (
    Path.home() / "AppData" / "Roaming" / "openfox" / "workflows" / "build-and-verify.workflow.json"
)
WORKFLOW_ID = "build-and-verify"


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    """WS_DIR temporaire contenant une copie du vrai workflow."""
    from app import config

    assert REAL_WORKFLOW.exists(), f"Workflow réel introuvable : {REAL_WORKFLOW}"
    (tmp_path / REAL_WORKFLOW.name).write_text(
        REAL_WORKFLOW.read_text(encoding="utf-8"), encoding="utf-8"
    )
    config.settings.ws_dir = str(tmp_path)
    client = TestClient(app)
    client.app.state.ws_dir = tmp_path
    return client


def _etag(response) -> str:
    return response.headers["ETag"]


def test_list_contains_workflow(client: TestClient) -> None:
    response = client.get("/api/workflows")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == WORKFLOW_ID


def test_get_detail_schema(client: TestClient) -> None:
    response = client.get(f"/api/workflows/{WORKFLOW_ID}")
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "steps" in data
    assert data["metadata"]["id"] == WORKFLOW_ID
    assert len(data["steps"]) >= 3


def test_validate_real_workflow_zero_errors(client: TestClient) -> None:
    response = client.post(f"/api/workflows/{WORKFLOW_ID}/validate")
    assert response.status_code == 200
    report = response.json()
    assert report["valid"] is True, f"Erreurs : {report['errors']}"
    assert report["errors"] == []


def test_put_adds_step_and_revalidates(client: TestClient) -> None:
    detail = client.get(f"/api/workflows/{WORKFLOW_ID}")
    etag = _etag(detail)
    wf = detail.json()
    wf["steps"].append(
        {
            "id": "s_final_check",
            "name": "Contrôle final",
            "type": "agent",
            "phase": "review",
            "agentId": "builder",
            "prompt": "Vérifie le résultat final avec {{workdir}}",
            "transitions": [{"goto": "$done"}],
        }
    )
    # Rattacher le nouvel step pour rester atteignable
    wf["steps"][-2]["transitions"] = [{"goto": "s_final_check"}]

    put = client.put(
        f"/api/workflows/{WORKFLOW_ID}",
        json=wf,
        headers={"If-Match": etag},
    )
    assert put.status_code == 200, put.text

    report = client.post(f"/api/workflows/{WORKFLOW_ID}/validate").json()
    assert report["valid"] is True, f"Erreurs : {report['errors']}"


def test_put_without_if_match_412(client: TestClient) -> None:
    detail = client.get(f"/api/workflows/{WORKFLOW_ID}")
    response = client.put(f"/api/workflows/{WORKFLOW_ID}", json=detail.json())
    assert response.status_code == 412


def test_delete_roundtrip(client: TestClient) -> None:
    detail = client.get(f"/api/workflows/{WORKFLOW_ID}")
    etag = _etag(detail)
    delete = client.delete(f"/api/workflows/{WORKFLOW_ID}", headers={"If-Match": etag})
    assert delete.status_code == 204
    assert client.get(f"/api/workflows/{WORKFLOW_ID}").status_code == 404


def test_export_native_relisible(client: TestClient) -> None:
    response = client.get(f"/api/workflows/{WORKFLOW_ID}/export")
    assert response.status_code == 200
    data = json.loads(response.content.decode("utf-8"))
    assert data["metadata"]["id"] == WORKFLOW_ID
    # Relisible par la validation (0 erreur)
    from app.validation import validate_workflow

    report = validate_workflow(data)
    assert report.valid is True, f"Erreurs : {report.errors}"


def test_export_bundle_content(client: TestClient) -> None:
    response = client.get("/api/export/bundle")
    assert response.status_code == 200
    content = response.content
    assert content[:2] == b"PK"  # signature zip
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert any(f"{WORKFLOW_ID}.workflow.json" in n for n in names)
        assert any(n.startswith("workflows/") for n in names)
        assert any(n == "manifest.json" for n in names)
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["schemaVersion"] == "1.0"