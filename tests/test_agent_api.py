"""Tests d'intégration des endpoints propose/apply (routes_agent.py).

Mocke le moteur de proposition et le client Ollama : aucun appel réseau réel.
"""

from __future__ import annotations

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
                "prompt": "Fais le travail avec {{workdir}}",
                "transitions": [{"goto": "$done"}],
            }
        ],
        "startCondition": {"type": "always"},
    }


def _proposed_workflow() -> dict:
    """Workflow proposé : prompt modifié, variables préservées."""
    wf = _workflow()
    wf["steps"][0]["prompt"] = "Fais le travail avec {{workdir}} et sois précis"
    return wf


class _FakeProposer:
    """Faux moteur de proposition : retourne une proposition valide."""

    def __init__(self, result=None) -> None:
        self.result = result

    def propose(self, workflow, scope, instruction, step_id=None, model=None):
        from app.agent_proposer import Proposal

        if self.result is not None:
            return self.result
        proposed = _proposed_workflow()
        return Proposal(
            success=True,
            proposed=proposed,
            diff={"added": [], "removed": [], "modified": ["s1"]},
            original_vars=["workdir"],
            lost_vars=[],
            preserves_vars=True,
        )


class _FakeOllama:
    def list_models(self) -> list[str]:
        return ["mistral-small3.2", "qwen2.5:32b"]


@pytest.fixture()
def fake_agent(monkeypatch) -> None:
    """Remplace le proposer et le client Ollama par des faux."""
    import app.routes_agent as routes_agent

    monkeypatch.setattr(routes_agent, "_proposer", _FakeProposer())
    monkeypatch.setattr(routes_agent, "_ollama", _FakeOllama())


def _create_demo(client: TestClient) -> None:
    response = client.post("/api/workflows", json=_workflow())
    assert response.status_code == 201


def test_get_models_returns_list(client: TestClient, fake_agent) -> None:
    response = client.get("/api/ollama/models")
    assert response.status_code == 200
    assert "mistral-small3.2" in response.json()["models"]


def test_propose_returns_proposal_id(client: TestClient, fake_agent) -> None:
    _create_demo(client)
    response = client.post(
        "/api/agent/propose",
        json={
            "workflow_id": "demo",
            "scope": "prompt",
            "step_id": "s1",
            "instruction": "Améliore le prompt",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "proposal_id" in payload
    assert payload["proposed"]["steps"][0]["prompt"].startswith("Fais le travail")
    assert payload["preserves_vars"] is True
    assert payload["validation"]["valid"] is True


def test_propose_unknown_workflow_404(client: TestClient, fake_agent) -> None:
    response = client.post(
        "/api/agent/propose",
        json={"workflow_id": "inexistant", "scope": "workflow", "instruction": "x"},
    )
    assert response.status_code == 404


def test_propose_invalid_scope_422(client: TestClient, fake_agent) -> None:
    _create_demo(client)
    response = client.post(
        "/api/agent/propose",
        json={"workflow_id": "demo", "scope": "invalide", "instruction": "x"},
    )
    assert response.status_code == 422


def test_apply_roundtrip_modifies_file(client: TestClient, fake_agent) -> None:
    _create_demo(client)
    propose = client.post(
        "/api/agent/propose",
        json={"workflow_id": "demo", "scope": "prompt", "step_id": "s1", "instruction": "Améliore"},
    )
    proposal_id = propose.json()["proposal_id"]

    apply = client.post("/api/agent/apply", json={"proposal_id": proposal_id})
    assert apply.status_code == 200
    assert "etag" in apply.json()

    # Le fichier sur disque a bien été modifié
    path = client.app.state.ws_dir / "demo.workflow.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "sois précis" in data["steps"][0]["prompt"]


def test_apply_without_propose_404(client: TestClient, fake_agent) -> None:
    _create_demo(client)
    response = client.post("/api/agent/apply", json={"proposal_id": "inconnu"})
    assert response.status_code == 404


def test_apply_after_external_change_409(client: TestClient, fake_agent) -> None:
    _create_demo(client)
    propose = client.post(
        "/api/agent/propose",
        json={"workflow_id": "demo", "scope": "workflow", "instruction": "Améliore"},
    )
    proposal_id = propose.json()["proposal_id"]

    # Modification externe du fichier entre propose et apply
    path = client.app.state.ws_dir / "demo.workflow.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["metadata"]["description"] = "Modifié ailleurs"
    path.write_text(json.dumps(data), encoding="utf-8")

    apply = client.post("/api/agent/apply", json={"proposal_id": proposal_id})
    assert apply.status_code == 409


def test_apply_blocked_when_vars_lost(client: TestClient, monkeypatch) -> None:
    """Une proposition qui perd des variables est bloquée à l'apply (400)."""
    import app.routes_agent as routes_agent
    from app.agent_proposer import Proposal

    _create_demo(client)
    lost = _proposed_workflow()
    lost["steps"][0]["prompt"] = "Prompt sans variable"
    fake = _FakeProposer(
        result=Proposal(
            success=True,
            proposed=lost,
            diff={"added": [], "removed": [], "modified": ["s1"]},
            original_vars=["workdir"],
            lost_vars=["workdir"],
            preserves_vars=False,
        )
    )
    monkeypatch.setattr(routes_agent, "_proposer", fake)
    monkeypatch.setattr(routes_agent, "_ollama", _FakeOllama())

    propose = client.post(
        "/api/agent/propose",
        json={"workflow_id": "demo", "scope": "workflow", "instruction": "Enlève la variable"},
    )
    assert propose.status_code == 200
    assert propose.json()["preserves_vars"] is False

    apply = client.post("/api/agent/apply", json={"proposal_id": propose.json()["proposal_id"]})
    assert apply.status_code == 400


def test_discard_removes_proposal(client: TestClient, fake_agent) -> None:
    _create_demo(client)
    propose = client.post(
        "/api/agent/propose",
        json={"workflow_id": "demo", "scope": "workflow", "instruction": "Améliore"},
    )
    proposal_id = propose.json()["proposal_id"]

    discard = client.post("/api/agent/discard", json={"proposal_id": proposal_id})
    assert discard.status_code == 204

    apply = client.post("/api/agent/apply", json={"proposal_id": proposal_id})
    assert apply.status_code == 404


def test_discard_unknown_404(client: TestClient, fake_agent) -> None:
    response = client.post("/api/agent/discard", json={"proposal_id": "inconnu"})
    assert response.status_code == 404