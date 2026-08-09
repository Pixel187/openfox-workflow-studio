"""Tests du moteur de proposition agent (agent_proposer.py)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.agent_proposer import AgentProposer
from app.ollama_client import OllamaClient


def _workflow() -> dict:
    return {
        "metadata": {
            "id": "demo",
            "name": "Demo",
            "description": "Test",
            "version": "1.0.0",
            "color": "#3b82f6",
        },
        "entryStep": "s1",
        "settings": {"maxIterations": 50},
        "steps": [
            {
                "id": "s1",
                "name": "S1",
                "type": "agent",
                "phase": "build",
                "agentId": "builder",
                "prompt": "Utilise {{workdir}} pour le travail",
                "transitions": [{"goto": "$done"}],
            }
        ],
        "startCondition": {"type": "always"},
    }


def _client_returning(payload: dict) -> OllamaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})

    return OllamaClient(base_url="http://fake:11434", transport=httpx.MockTransport(handler))


def test_propose_workflow_scope_adds_step() -> None:
    proposed = json.loads(json.dumps(_workflow()))
    proposed["steps"][0]["transitions"] = [{"goto": "s2"}]
    proposed["steps"].append(
        {
            "id": "s2",
            "name": "S2",
            "type": "agent",
            "phase": "build",
            "agentId": "builder",
            "prompt": "Deuxième étape",
            "transitions": [{"goto": "$done"}],
        }
    )
    client = _client_returning(proposed)
    result = AgentProposer(client).propose(_workflow(), scope="workflow", instruction="Ajoute une étape")
    assert result.proposed["steps"][1]["id"] == "s2"
    assert result.diff["added"] == [{"id": "s2", "name": "S2"}]
    assert result.preserves_vars is True


def test_diff_modified_includes_field_changes() -> None:
    proposed = json.loads(json.dumps(_workflow()))
    proposed["steps"][0]["prompt"] = "Nouveau prompt avec {{workdir}}"
    client = _client_returning(proposed)
    result = AgentProposer(client).propose(
        _workflow(), scope="prompt", step_id="s1", instruction="Améliore le prompt"
    )
    assert result.success is True
    modified = result.diff["modified"]
    assert len(modified) == 1
    assert modified[0]["id"] == "s1"
    assert modified[0]["name"] == "S1"
    prompt_change = next(c for c in modified[0]["changes"] if c["field"] == "prompt")
    assert prompt_change["before"] == "Utilise {{workdir}} pour le travail"
    assert prompt_change["after"] == "Nouveau prompt avec {{workdir}}"


def test_propose_prompt_scope_only_changes_prompt() -> None:
    proposed = json.loads(json.dumps(_workflow()))
    proposed["steps"][0]["prompt"] = "Nouveau prompt avec {{workdir}}"
    client = _client_returning(proposed)
    result = AgentProposer(client).propose(
        _workflow(), scope="prompt", step_id="s1", instruction="Améliore le prompt"
    )
    assert result.success is True
    assert result.proposed["steps"][0]["prompt"] == "Nouveau prompt avec {{workdir}}"
    assert result.preserves_vars is True


def test_variable_loss_detected() -> None:
    proposed = json.loads(json.dumps(_workflow()))
    proposed["steps"][0]["prompt"] = "Prompt sans variable"
    client = _client_returning(proposed)
    result = AgentProposer(client).propose(
        _workflow(), scope="prompt", step_id="s1", instruction="Enlève la variable"
    )
    assert result.success is True
    assert result.preserves_vars is False
    assert "workdir" in result.lost_vars


def test_invalid_json_returns_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "pas du json"}}]}
        )

    client = OllamaClient(base_url="http://fake:11434", transport=httpx.MockTransport(handler))
    result = AgentProposer(client).propose(_workflow(), scope="workflow", instruction="x")
    assert result.success is False
    assert "JSON" in result.error


def test_invalid_scope_rejected() -> None:
    client = _client_returning(_workflow())
    with pytest.raises(ValueError, match="scope"):
        AgentProposer(client).propose(_workflow(), scope="invalide", instruction="x")


def test_proposed_workflow_validated() -> None:
    proposed = dict(_workflow())
    proposed["steps"][0]["transitions"][0]["goto"] = "s99_inexistant"
    client = _client_returning(proposed)
    result = AgentProposer(client).propose(_workflow(), scope="workflow", instruction="casse")
    assert result.success is False
    assert any("s99_inexistant" in e for e in result.validation_errors)