"""Tests de la base d'agents (agent_base.py + routes_agent_base.py)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import agent_base
from app.main import app

SEED_COUNT = len(agent_base._SEED_TEMPLATES)


@pytest.fixture()
def base_dir(tmp_path: Path) -> Path:
    """Répertoire temporaire pour la base d'agents."""
    original = agent_base.AGENT_BASE_DIR
    agent_base.AGENT_BASE_DIR = tmp_path
    yield tmp_path
    agent_base.AGENT_BASE_DIR = original


def test_seed_creates_all_templates(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    files = sorted(p.name for p in base_dir.glob("*.json"))
    assert len(files) == SEED_COUNT


def test_seed_covers_four_collections(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    templates = agent_base.list_templates()
    collections = {t["collection"] for t in templates}
    assert collections == {"general", "codage", "redaction", "juridique"}


def test_list_templates_after_seed(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    templates = agent_base.list_templates()
    assert len(templates) == SEED_COUNT
    ids = {t["id"] for t in templates}
    assert {"planner", "builder-drafter", "verifier"} <= ids
    assert {"architecte", "implementateur", "debugger"} <= ids
    assert {"planificateur-livre", "redacteur", "relecteur"} <= ids
    assert {"analyste-dossier", "redacteur-juridique", "verificateur-conformite"} <= ids


def test_get_template(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    template = agent_base.get_template("planner")
    assert template["id"] == "planner"
    assert template["phase"] == "planning"
    assert "prompt" in template


def test_get_template_missing_raises(base_dir: Path) -> None:
    with pytest.raises(KeyError):
        agent_base.get_template("inexistant")


def test_save_and_delete_template(base_dir: Path) -> None:
    template = {
        "id": "custom",
        "name": "Custom",
        "description": "Gabarit custom",
        "collection": "codage",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": "Fais le travail",
    }
    agent_base.save_template(template)
    assert agent_base.get_template("custom")["name"] == "Custom"
    agent_base.delete_template("custom")
    with pytest.raises(KeyError):
        agent_base.get_template("custom")


def test_delete_missing_raises(base_dir: Path) -> None:
    with pytest.raises(KeyError):
        agent_base.delete_template("inexistant")


def test_api_agent_base_returns_seed(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    client = TestClient(app)
    response = client.get("/api/agent-base")
    assert response.status_code == 200
    assert len(response.json()) == SEED_COUNT


def test_verifier_has_verifier_findings_pattern(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    verifier = agent_base.get_template("verifier")
    assert "verifierFindings" in verifier["prompt"]


def test_api_create_template(base_dir: Path) -> None:
    client = TestClient(app)
    payload = {
        "id": "nouveau-agent",
        "name": "Nouvel agent",
        "description": "Test",
        "collection": "codage",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": "Fais le travail",
    }
    response = client.post("/api/agent-base", json=payload)
    assert response.status_code == 201
    assert response.json()["id"] == "nouveau-agent"
    assert agent_base.get_template("nouveau-agent")["collection"] == "codage"


def test_api_create_duplicate_409(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    client = TestClient(app)
    payload = {
        "id": "planner",
        "name": "Doublon",
        "collection": "general",
        "type": "agent",
        "phase": "planning",
        "agentId": "builder",
        "subGroup": "planning",
        "prompt": "x",
    }
    response = client.post("/api/agent-base", json=payload)
    assert response.status_code == 409


def test_api_create_invalid_collection_422(base_dir: Path) -> None:
    client = TestClient(app)
    payload = {
        "id": "bad",
        "name": "Bad",
        "collection": "inexistante",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": "x",
    }
    response = client.post("/api/agent-base", json=payload)
    assert response.status_code == 422


def test_api_update_template(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    client = TestClient(app)
    payload = {
        "id": "planner",
        "name": "Planner v2",
        "description": "Modifié",
        "collection": "general",
        "type": "agent",
        "phase": "planning",
        "agentId": "builder",
        "subGroup": "planning",
        "prompt": "Nouveau prompt",
    }
    response = client.put("/api/agent-base/planner", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Planner v2"
    assert agent_base.get_template("planner")["prompt"] == "Nouveau prompt"


def test_api_update_missing_404(base_dir: Path) -> None:
    client = TestClient(app)
    payload = {
        "id": "absent",
        "name": "Absent",
        "collection": "general",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": "x",
    }
    response = client.put("/api/agent-base/absent", json=payload)
    assert response.status_code == 404


def test_api_delete_template(base_dir: Path) -> None:
    agent_base.seed_if_empty()
    client = TestClient(app)
    response = client.delete("/api/agent-base/planner")
    assert response.status_code == 204
    assert client.get("/api/agent-base/planner").status_code == 404


def test_api_delete_missing_404(base_dir: Path) -> None:
    client = TestClient(app)
    response = client.delete("/api/agent-base/absent")
    assert response.status_code == 404