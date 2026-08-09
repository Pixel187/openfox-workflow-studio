"""Tests du générateur de gabarits d'agents (agent_generator.py).

Mocke le client Ollama : aucun appel réseau réel.
"""

from __future__ import annotations

import json

import pytest

from app.agent_generator import AgentGenerator


class _FakeClient:
    """Client Ollama factice : retourne les réponses dans l'ordre."""

    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[str | None] = []

    def ask(self, system: str, user: str, model: str | None = None, **kwargs) -> str:
        self.calls.append(model)
        if not self.responses:
            raise ValueError("plus de réponses")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _valid_template_json() -> str:
    return json.dumps(
        {
            "id": "auditeur-rgpd",
            "name": "Auditeur RGPD",
            "description": "Vérifie la conformité RGPD d'un dossier.",
            "collection": "juridique",
            "type": "sub_agent",
            "phase": "verification",
            "agentId": "builder",
            "subAgentType": "verifier",
            "subGroup": "verify",
            "prompt": "Vérifie la conformité RGPD. step_done()",
            "nudgePrompt": "Cite les sources officielles.",
        }
    )


def test_generate_returns_valid_template() -> None:
    client = _FakeClient([_valid_template_json()])
    generator = AgentGenerator(client=client)
    template = generator.generate("Un agent qui audite la conformité RGPD", collection="juridique")
    assert template["id"] == "auditeur-rgpd"
    assert template["name"] == "Auditeur RGPD"
    assert template["collection"] == "juridique"
    assert template["type"] == "sub_agent"
    assert template["prompt"].startswith("Vérifie la conformité RGPD")
    assert client.calls == [None]


def test_generate_uses_requested_model() -> None:
    client = _FakeClient([_valid_template_json()])
    generator = AgentGenerator(client=client)
    generator.generate("Audit RGPD", model="qwen2.5:32b")
    assert client.calls == ["qwen2.5:32b"]


def test_generate_invalid_json_raises() -> None:
    client = _FakeClient(["pas du json du tout"])
    generator = AgentGenerator(client=client)
    with pytest.raises(ValueError, match="non-JSON"):
        generator.generate("Audit RGPD")


def test_generate_missing_required_field_raises() -> None:
    payload = json.dumps({"id": "x", "name": "X"})
    client = _FakeClient([payload])
    generator = AgentGenerator(client=client)
    with pytest.raises(ValueError, match="prompt"):
        generator.generate("Audit RGPD")


def test_generate_fallback_model_on_error() -> None:
    client = _FakeClient([ValueError("Ollama down"), _valid_template_json()])
    generator = AgentGenerator(client=client)
    template = generator.generate("Audit RGPD", model="qwen2.5:32b")
    assert template["id"] == "auditeur-rgpd"
    assert client.calls == ["qwen2.5:32b", "mistral-small3.2"]


def test_generate_no_fallback_when_default_model_fails() -> None:
    client = _FakeClient([ValueError("Ollama down")])
    generator = AgentGenerator(client=client)
    with pytest.raises(ValueError, match="Ollama down"):
        generator.generate("Audit RGPD", model=None)
    assert client.calls == [None]