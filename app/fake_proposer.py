"""Proposer déterministe pour les tests E2E (activé par WS_FAKE_PROPOSER=1).

Purpose: Remplacer AgentProposer par une implémentation déterministe qui ne
contacte jamais Ollama, pour des tests E2E reproductibles.
Responsibilities:
  - scope workflow : ajoute une étape "s2" au workflow
  - scope step/prompt : modifie le prompt de l'étape cible
Dependencies: agent_proposer.Proposal
Usage examples:
    WS_FAKE_PROPOSER=1 python -m uvicorn app.main:app --port 8761
"""

from __future__ import annotations

import json
from typing import Any

from app.agent_proposer import Proposal


class FakeProposer:
    """Propose une modification déterministe, sans appel réseau."""

    def propose(
        self,
        workflow: dict[str, Any],
        scope: str,
        instruction: str,
        step_id: str | None = None,
        model: str | None = None,
    ) -> Proposal:
        proposed = json.loads(json.dumps(workflow))
        if scope == "workflow":
            proposed["steps"].append(
                {
                    "id": "s2",
                    "name": "Étape IA",
                    "type": "agent",
                    "phase": "build",
                    "agentId": "builder",
                    "prompt": "Étape ajoutée par l'assistant",
                    "transitions": [{"goto": "$done"}],
                }
            )
            if proposed["steps"]:
                proposed["steps"][0]["transitions"] = [{"goto": "s2"}]
            diff = {
                "added": [{"id": "s2", "name": "Étape IA"}],
                "removed": [],
                "modified": [
                    {
                        "id": "s1",
                        "name": proposed["steps"][0]["name"] if proposed["steps"] else "s1",
                        "changes": [
                            {
                                "field": "transitions",
                                "before": [{"goto": "$done"}],
                                "after": [{"goto": "s2"}],
                            }
                        ],
                    }
                ],
            }
        else:
            target = step_id or proposed["steps"][0]["id"]
            for step in proposed["steps"]:
                if step["id"] == target:
                    step["prompt"] = step["prompt"] + " (amélioré par l'assistant)"
                    break
            diff = {
                "added": [],
                "removed": [],
                "modified": [
                    {
                        "id": target,
                        "name": next(
                            (s["name"] for s in proposed["steps"] if s["id"] == target),
                            target,
                        ),
                        "changes": [{"field": "prompt", "before": "", "after": ""}],
                    }
                ],
            }
        return Proposal(
            success=True,
            proposed=proposed,
            diff=diff,
            original_vars=[],
            lost_vars=[],
            preserves_vars=True,
        )