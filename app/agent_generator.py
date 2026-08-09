"""Générateur de gabarits d'agents via Ollama.

Purpose: Générer un gabarit d'agent complet (id, name, prompt, nudgePrompt…)
à partir d'une description en langage naturel, sans écrire sur disque.
Responsibilities:
  - Construire le system/user prompt (FR, JSON strict)
  - Appeler ollama_client.ask, parser le JSON
  - Valider les champs requis du gabarit
  - Fallback sur le modèle par défaut si le modèle demandé échoue
Dependencies: ollama_client, config
Usage examples:
    from app.agent_generator import AgentGenerator
    template = AgentGenerator().generate("Audit RGPD", collection="juridique")
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import settings
from app.ollama_client import OllamaClient

_SYSTEM_PROMPT = """Tu es un expert en conception d'agents IA pour OpenFox.
Tu produis UNIQUEMENT du JSON valide, sans texte avant ni après.

RÈGLES STRICTES :
1. id : kebab-case minuscules (a-z, 0-9, tirets), dérivé du nom.
2. name : nom court et parlant.
3. description : une phrase décrivant le rôle.
4. type : "agent" ou "sub_agent" (sub_agent pour vérification/relecture).
5. phase : "planning", "build", "verification" ou "review".
6. agentId : toujours "builder".
7. subAgentType : "verifier" ou "code_reviewer" si type=sub_agent, sinon absent.
8. subGroup : "planning", "build", "verify" ou "review".
9. prompt : en français, détaillé, actionnable, avec step_done() ou return_value() à la fin.
10. nudgePrompt : conseil de style en une phrase.
11. NE PAS inventer d'outils ni de fonctions.
12. Réponds UNIQUEMENT avec le JSON brut."""


class AgentGenerator:
    """Génère un gabarit d'agent complet à partir d'une description."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def generate(
        self,
        description: str,
        collection: str = "general",
        model: str | None = None,
    ) -> dict[str, Any]:
        """Génère un gabarit. Fallback sur le modèle par défaut si demandé et en échec."""
        user_prompt = (
            f"Description de l'agent : {description}\n"
            f"Collection : {collection}\n\n"
            "Retourne le JSON complet du gabarit."
        )
        try:
            raw = self.client.ask(_SYSTEM_PROMPT, user_prompt, model=model)
        except ValueError as exc:
            if model and model != settings.ollama_model:
                raw = self.client.ask(_SYSTEM_PROMPT, user_prompt, model=settings.ollama_model)
            else:
                raise ValueError(str(exc)) from exc

        template = self._extract_json(raw)
        if template is None:
            raise ValueError("Réponse non-JSON du modèle")
        self._validate(template)
        return template

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        m = re.search(r"```(?:json)?\s*\n?(.*?)(?:\n|\r\n)?```", text, re.DOTALL)
        if m:
            text = m.group(1)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _validate(self, template: dict[str, Any]) -> None:
        required = ("id", "name", "description", "type", "phase", "agentId", "prompt")
        missing = [field for field in required if not template.get(field)]
        if missing:
            raise ValueError(f"Gabarit incomplet, champs manquants : {', '.join(missing)}")
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", template["id"]):
            raise ValueError("id invalide : kebab-case minuscules attendu")
        if template["type"] not in ("agent", "sub_agent"):
            raise ValueError("type invalide : agent ou sub_agent attendu")
        if template["phase"] not in ("planning", "build", "verification", "review"):
            raise ValueError("phase invalide")