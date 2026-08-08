"""Tests du client Ollama (ollama_client.py) avec httpx MockTransport."""

from __future__ import annotations

import json

import httpx
import pytest

from app.ollama_client import OllamaClient


def _client_with_transport(handler) -> OllamaClient:
    transport = httpx.MockTransport(handler)
    return OllamaClient(base_url="http://fake:11434", transport=transport)


def test_list_models_from_tags() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "mistral-small3.2"}, {"name": "qwen2.5:32b"}]},
        )

    client = _client_with_transport(handler)
    assert client.list_models() == ["mistral-small3.2", "qwen2.5:32b"]


def test_list_models_fallback_v1() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "model-a"}]})

    client = _client_with_transport(handler)
    assert client.list_models() == ["model-a"]


def test_ask_returns_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.read().decode())
        assert payload["temperature"] == 0.3
        assert payload["max_tokens"] == 8192
        assert payload["stream"] is False
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Réponse du modèle"}}]},
        )

    client = _client_with_transport(handler)
    result = client.ask("system", "user")
    assert result == "Réponse du modèle"


def test_ask_http_error_raises_valueerror() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    client = _client_with_transport(handler)
    with pytest.raises(ValueError, match="HTTP 500"):
        client.ask("system", "user")


def test_ask_timeout_raises_valueerror() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = _client_with_transport(handler)
    with pytest.raises(ValueError, match="timeout"):
        client.ask("system", "user")


def test_ask_retries_once_on_transient_error() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "ok"}}]}
        )

    client = _client_with_transport(handler)
    assert client.ask("system", "user") == "ok"
    assert calls["count"] == 2


def test_custom_model_and_temperature() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read().decode())
        assert payload["model"] == "custom-model"
        assert payload["temperature"] == 0.7
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "x"}}]}
        )

    client = _client_with_transport(handler)
    client.ask("system", "user", model="custom-model", temperature=0.7)