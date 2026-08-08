"""Moteur de proposition agent : propose des modifications de workflow via Ollama.

Purpose: Générer une proposition de modification (workflow/step/prompt) via Ollama,
sans jamais écrire sur disque (l'approbation est séparée, endpoint apply).
Responsibilities:
  - Construire system/user prompts (FR, règles strictes)
  - Appeler ollama_client.ask, parser le JSON
  - Valider la proposition (validation.validate_workflow)
  - Détecter la perte de variables {{...}} (preservation)
Dependencies: ollama_client, validation, variables
Usage examples:
    from app.agent_proposer import AgentProposer
    result = AgentProposer().propose(wf, scope="workflow", instruction="...")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.ollama_client import OllamaClient
from app.validation import validate_workflow
from app.variables import find_template_vars

_SYSTEM_PROMPT = """Tu es un expert en édition de workflows OpenFox.
Tu produis UNIQUEMENT du JSON valide, sans texte avant ni après.

RÈGLES STRICTES :
1. NE PAS supprimer ni renommer les variables {{...}} existantes dans les prompts.
2. Conserver la structure JSON valide du workflow (metadata, entryStep, settings, steps, startCondition).
3. NE PAS inventer d'outils ni de fonctions.
4. Toutes les étapes : "agentId": "builder" (jamais "planner").
5. Prompts en français, sans code.
6. Transitions cohérentes : chaque goto pointe vers une étape existante ou "$done".
7. Réponds UNIQUEMENT avec le JSON brut modifié."""


@dataclass
class Proposal:
    """Résultat d'une proposition : succès, contenu proposé, diff, préservation."""

    success: bool
    proposed: dict[str, Any] | None = None
    diff: dict[str, list[str]] = field(default_factory=lambda: {"added": [], "removed": [], "modified": []})
    original_vars: list[str] = field(default_factory=list)
    lost_vars: list[str] = field(default_factory=list)
    preserves_vars: bool = True
    validation_errors: list[str] = field(default_factory=list)
    error: str = ""


class AgentProposer:
    """Moteur de proposition : workflow, step ou prompt."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def propose(
        self,
        workflow: dict[str, Any],
        scope: str,
        instruction: str,
        step_id: str | None = None,
        model: str | None = None,
    ) -> Proposal:
        """Génère une proposition pour le scope demandé."""
        if scope not in ("workflow", "step", "prompt"):
            raise ValueError(f"scope invalide : {scope}")

        original_vars = find_template_vars(json.dumps(workflow, ensure_ascii=False))
        user_prompt = self._build_user_prompt(workflow, scope, instruction, step_id)

        try:
            raw = self.client.ask(_SYSTEM_PROMPT, user_prompt, model=model)
        except ValueError as exc:
            return Proposal(success=False, error=str(exc))

        proposed = self._extract_json(raw)
        if proposed is None:
            return Proposal(success=False, error="Réponse non-JSON du modèle")

        if scope in ("step", "prompt"):
            proposed = self._merge_step(workflow, proposed, step_id, scope)

        report = validate_workflow(proposed)
        if not report.valid:
            return Proposal(
                success=False,
                proposed=proposed,
                validation_errors=report.errors,
                error="Proposition invalide",
            )

        proposed_vars = find_template_vars(json.dumps(proposed, ensure_ascii=False))
        lost = [v for v in original_vars if v not in proposed_vars]

        return Proposal(
            success=True,
            proposed=proposed,
            diff=self._compute_diff(workflow, proposed),
            original_vars=original_vars,
            lost_vars=lost,
            preserves_vars=len(lost) == 0,
        )

    def _build_user_prompt(
        self,
        workflow: dict[str, Any],
        scope: str,
        instruction: str,
        step_id: str | None,
    ) -> str:
        if scope == "workflow":
            target = json.dumps(workflow, indent=2, ensure_ascii=False)
        elif scope == "step":
            step = self._find_step(workflow, step_id)
            target = json.dumps(step, indent=2, ensure_ascii=False)
        else:  # prompt
            step = self._find_step(workflow, step_id)
            target = step.get("prompt", "")
        return f"Instruction : {instruction}\n\nContenu à modifier :\n{target}\n\nRetourne le JSON complet modifié."

    def _find_step(self, workflow: dict[str, Any], step_id: str | None) -> dict[str, Any]:
        for step in workflow.get("steps", []):
            if step.get("id") == step_id:
                return step
        raise ValueError(f"step_id '{step_id}' introuvable")

    def _merge_step(
        self,
        workflow: dict[str, Any],
        proposed_step: dict[str, Any],
        step_id: str | None,
        scope: str,
    ) -> dict[str, Any]:
        """Réintègre l'étape modifiée dans le workflow complet.

        Le JSON retourné par le modèle peut être le workflow complet (clé "steps")
        ou l'étape seule : on extrait l'étape correspondante dans les deux cas.
        """
        merged = json.loads(json.dumps(workflow))
        if "steps" in proposed_step:
            proposed_step = next(
                (s for s in proposed_step["steps"] if s.get("id") == step_id),
                proposed_step,
            )
        for i, step in enumerate(merged.get("steps", [])):
            if step.get("id") == step_id:
                if scope == "prompt":
                    merged["steps"][i]["prompt"] = proposed_step.get("prompt", step.get("prompt", ""))
                else:
                    merged["steps"][i] = proposed_step
                break
        return merged

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

    def _compute_diff(
        self, original: dict[str, Any], proposed: dict[str, Any]
    ) -> dict[str, list[str]]:
        orig_ids = {s.get("id") for s in original.get("steps", [])}
        prop_ids = {s.get("id") for s in proposed.get("steps", [])}
        added = sorted(prop_ids - orig_ids)
        removed = sorted(orig_ids - prop_ids)
        modified = sorted(
            sid
            for sid in orig_ids & prop_ids
            if self._step_changed(original, proposed, sid)
        )
        return {"added": added, "removed": removed, "modified": modified}

    def _step_changed(self, original: dict[str, Any], proposed: dict[str, Any], sid: str) -> bool:
        orig = next(s for s in original.get("steps", []) if s.get("id") == sid)
        prop = next(s for s in proposed.get("steps", []) if s.get("id") == sid)
        return orig != prop