"""Client Ollama : découverte de modèles + chat.

Purpose: Appeler l'API Ollama (découverte de modèles, chat completions).
Responsibilities:
  - list_models : GET /api/tags avec fallback /v1/models
  - ask : POST /v1/chat/completions (OpenAI-style), timeout 180s, retry 1x
Dependencies: httpx, config
Usage examples:
    from app.ollama_client import OllamaClient
    client = OllamaClient()
    models = client.list_models()
    text = client.ask("system", "user")
"""

from __future__ import annotations

import httpx

from app.config import settings


class OllamaClient:
    """Client minimal pour l'API Ollama (mockable via transport httpx)."""

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.transport = transport

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        with httpx.Client(transport=self.transport, timeout=180.0) as client:
            return client.request(method, url, **kwargs)

    def list_models(self) -> list[str]:
        """Liste les modèles disponibles (GET /api/tags, fallback /v1/models)."""
        try:
            resp = self._request("GET", "/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except httpx.HTTPStatusError:
            resp = self._request("GET", "/v1/models")
            resp.raise_for_status()
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]

    def ask(
        self,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Appelle le chat completions et retourne le texte. Retry 1x."""
        payload = {
            "model": model or settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        for attempt in range(2):
            try:
                resp = self._request(
                    "POST",
                    "/v1/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as exc:
                if attempt == 0:
                    continue
                raise ValueError(f"Ollama HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
            except httpx.HTTPError as exc:
                if attempt == 0:
                    continue
                raise ValueError(f"Ollama erreur réseau: {exc}") from exc
        raise ValueError("Ollama: échec après 2 tentatives")