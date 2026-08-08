"""OpenFox Workflow Codec — Encodage et décodage des workflows avec variables de template.

Ce module fournit :
1. Un catalogue de variables de template disponibles
2. Un encodeur pour sérialiser des étapes de workflow
3. Un décodeur pour valider et interpréter les workflows
4. Des helpers pour substituer les variables dans les prompts
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ── Variables de template disponibles ─────────────────────────────────────────

class TemplateVar(Enum):
    """Variables injectées par le runtime OpenFox dans les prompts."""

    # Répertoire de travail du workflow
    WORKDIR = "workdir"

    # Identifiant de l'étape courante
    STEP_ID = "stepId"

    # Identifiant de l'agent courant
    AGENT_ID = "agentId"

    # Type de sous-agent (pour sub_agent)
    SUB_AGENT_TYPE = "subAgentType"

    # Identifiant de session
    SESSION_ID = "sessionId"

    # Identifiant de cas/dossier
    CASE_ID = "caseId"

    # Nom du workflow
    WORKFLOW_NAME = "workflowName"

    # Description du workflow
    WORKFLOW_DESCRIPTION = "workflowDescription"

    # Version du workflow
    WORKFLOW_VERSION = "workflowVersion"


TEMPLATE_VAR_NAMES: list[str] = [v.value for v in TemplateVar]

TEMPLATE_PATTERN = re.compile(
    r"\{\{\s*(" + "|".join(re.escape(v) for v in TEMPLATE_VAR_NAMES) + r")\s*\}\}"
)


# ── Contexte de template ──────────────────────────────────────────────────────

@dataclass
class TemplateContext:
    """Contexte pour la substitution des variables de template."""

    workdir: str = ""
    step_id: str = ""
    agent_id: str = ""
    sub_agent_type: str = ""
    session_id: str = ""
    case_id: str = ""
    workflow_name: str = ""
    workflow_description: str = ""
    workflow_version: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "workdir": self.workdir,
            "stepId": self.step_id,
            "agentId": self.agent_id,
            "subAgentType": self.sub_agent_type,
            "sessionId": self.session_id,
            "caseId": self.case_id,
            "workflowName": self.workflow_name,
            "workflowDescription": self.workflow_description,
            "workflowVersion": self.workflow_version,
        }

    def substitute(self, text: str) -> str:
        """Substitue toutes les variables {{...}} dans le texte."""
        result = text
        for var in TemplateVar:
            placeholder = "{{" + var.value + "}}"
            value = getattr(self, var.value, "")
            result = result.replace(placeholder, value)
        return result


# ── Modèles de données workflow ───────────────────────────────────────────────

@dataclass
class WorkflowMetadata:
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    color: str = "#3b82f6"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowMetadata:
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            color=data.get("color", "#3b82f6"),
        )


@dataclass
class WorkflowTransition:
    when: dict[str, Any] = field(default_factory=lambda: {"type": "always"})
    goto: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"when": self.when, "goto": self.goto}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowTransition:
        return cls(when=data.get("when", {"type": "always"}), goto=data.get("goto", ""))


@dataclass
class WorkflowStep:
    id: str
    name: str
    type: str = "agent"
    phase: str = "build"
    agent_id: str = "builder"
    sub_agent_type: str = ""
    sub_group: str = ""
    prompt: str = ""
    nudge_prompt: str = ""
    transitions: list[WorkflowTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "phase": self.phase,
            "agentId": self.agent_id,
            "prompt": self.prompt,
        }
        if self.sub_agent_type:
            data["subAgentType"] = self.sub_agent_type
        if self.sub_group:
            data["subGroup"] = self.sub_group
        if self.nudge_prompt:
            data["nudgePrompt"] = self.nudge_prompt
        if self.transitions:
            data["transitions"] = [t.to_dict() for t in self.transitions]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowStep:
        transitions = [
            WorkflowTransition.from_dict(t) for t in data.get("transitions", [])
        ]
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", "agent"),
            phase=data.get("phase", "build"),
            agent_id=data.get("agentId", "builder"),
            sub_agent_type=data.get("subAgentType", ""),
            sub_group=data.get("subGroup", ""),
            prompt=data.get("prompt", ""),
            nudge_prompt=data.get("nudgePrompt", ""),
            transitions=transitions,
        )


@dataclass
class WorkflowDefinition:
    metadata: WorkflowMetadata
    entry_step: str
    settings: dict[str, Any] = field(default_factory=lambda: {"maxIterations": 50})
    steps: list[WorkflowStep] = field(default_factory=list)
    start_condition: dict[str, Any] = field(default_factory=lambda: {"type": "always"})

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "entryStep": self.entry_step,
            "settings": self.settings,
            "steps": [s.to_dict() for s in self.steps],
            "startCondition": self.start_condition,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowDefinition:
        metadata = WorkflowMetadata.from_dict(data.get("metadata", {}))
        steps = [WorkflowStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            metadata=metadata,
            entry_step=data.get("entryStep", ""),
            settings=data.get("settings", {"maxIterations": 50}),
            steps=steps,
            start_condition=data.get("startCondition", {"type": "always"}),
        )


# ── Encodeur / Décodeur ───────────────────────────────────────────────────────

class WorkflowCodec:
    """Encodeur et décodeur de workflows OpenFox."""

    @staticmethod
    def encode(workflow: WorkflowDefinition) -> str:
        """Sérialise un workflow en JSON."""
        return json.dumps(workflow.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def decode(text: str) -> WorkflowDefinition:
        """Désérialise un workflow depuis JSON."""
        data = json.loads(text)
        return WorkflowDefinition.from_dict(data)

    @staticmethod
    def load(path: str | Path) -> WorkflowDefinition:
        """Charge un workflow depuis un fichier."""
        text = Path(path).read_text(encoding="utf-8")
        return WorkflowCodec.decode(text)

    @staticmethod
    def save(workflow: WorkflowDefinition, path: str | Path) -> None:
        """Sauvegarde un workflow dans un fichier."""
        Path(path).write_text(WorkflowCodec.encode(workflow), encoding="utf-8")

    @staticmethod
    def substitute_prompt(prompt: str, context: TemplateContext) -> str:
        """Substitue les variables de template dans un prompt."""
        return context.substitute(prompt)

    @staticmethod
    def validate(workflow: WorkflowDefinition) -> list[str]:
        """Valide un workflow et retourne les erreurs."""
        errors: list[str] = []

        if not workflow.metadata.id:
            errors.append("metadata.id manquant")
        if not workflow.metadata.name:
            errors.append("metadata.name manquant")
        if not workflow.entry_step:
            errors.append("entryStep manquant")

        step_ids = [s.id for s in workflow.steps]
        if workflow.entry_step not in step_ids:
            errors.append(f"entryStep '{workflow.entry_step}' introuvable dans steps")

        seen_ids = set()
        for s in workflow.steps:
            if s.id in seen_ids:
                errors.append(f"ID en double : {s.id}")
            seen_ids.add(s.id)

            if s.type == "sub_agent" and not s.sub_agent_type:
                errors.append(f"[{s.id}] sub_agent sans subAgentType")

            for t in s.transitions:
                g = t.goto
                if g and g not in step_ids and g != "$done":
                    errors.append(f"[{s.id}] goto '{g}' ne correspond à aucune étape")

        return errors

    @staticmethod
    def list_template_vars() -> list[str]:
        """Retourne la liste des variables de template disponibles."""
        return TEMPLATE_VAR_NAMES

    @staticmethod
    def find_template_vars(text: str) -> list[str]:
        """Trouve toutes les variables de template dans un texte."""
        matches = TEMPLATE_PATTERN.findall(text)
        return list(set(matches))


# ── Workflow prédéfini : build-and-verify ─────────────────────────────────────

def create_build_verify_workflow(
    workflow_id: str = "build-and-verify",
    name: str = "Build and Verify",
    description: str = "Workflow generique build/verify/review",
) -> WorkflowDefinition:
    """Crée un workflow build-and-verify prêt à l'emploi."""

    metadata = WorkflowMetadata(
        id=workflow_id,
        name=name,
        description=description,
        version="3.0.0",
        color="#3b82f6",
    )

    steps = [
        WorkflowStep(
            id="s01_build",
            name="Build",
            type="agent",
            phase="build",
            agent_id="builder",
            prompt=(
                "Dépôt : {{workdir}}.\n\n"
                "1. [Execute le travail de build demande]\n"
                "2. write_file(path=\"{{workdir}}/_build_output.md\", content=\"# Build output\\n\\n## Resultat\\n[resultat]\\n\\n## Details\\n[details]\")\n"
                "3. session_metadata(action=\"add\", key=\"criteria\", description=\"Build execute\", status=\"completed\")\n"
                "4. step_done()"
            ),
            transitions=[WorkflowTransition(goto="s02_verify")],
        ),
        WorkflowStep(
            id="s02_verify",
            name="Verify",
            type="sub_agent",
            phase="verification",
            agent_id="builder",
            sub_agent_type="verifier",
            prompt=(
                "Dépôt : {{workdir}}.\n\n"
                "1. session_metadata(action=\"get\", key=\"criteria\")\n"
                "2. read_file(path=\"{{workdir}}/_build_output.md\")\n"
                "3. session_metadata(action=\"update\", key=\"criteria\", id=\"0\", status=\"passed\")\n"
                "4. return_value(content=\"Build verifie\")"
            ),
            transitions=[WorkflowTransition(goto="s03_review")],
        ),
        WorkflowStep(
            id="s03_review",
            name="Review",
            type="sub_agent",
            phase="review",
            agent_id="builder",
            sub_agent_type="code_reviewer",
            prompt=(
                "Dépôt : {{workdir}}.\n\n"
                "1. session_metadata(action=\"get\", key=\"review_findings\")\n"
                "2. read_file(path=\"{{workdir}}/_build_output.md\")\n"
                "3. session_metadata(action=\"update\", key=\"review_findings\", id=\"0\", status=\"resolved\")\n"
                "4. return_value(content=\"Revue terminee\")"
            ),
            transitions=[WorkflowTransition(goto="$done")],
        ),
    ]

    return WorkflowDefinition(
        metadata=metadata,
        entry_step="s01_build",
        settings={"maxIterations": 50},
        steps=steps,
        start_condition={"type": "always"},
    )


# ── CLI rapide ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  workflow_codec.py list-vars")
        print("  workflow_codec.py validate <workflow.json>")
        print("  workflow_codec.py build-and-verify [output.json]")
        sys.exit(0)

    command = sys.argv[1]

    if command == "list-vars":
        print("Variables de template disponibles :")
        for var in WorkflowCodec.list_template_vars():
            print(f"  {var}")

    elif command == "validate" and len(sys.argv) >= 3:
        path = sys.argv[2]
        try:
            workflow = WorkflowCodec.load(path)
            errors = WorkflowCodec.validate(workflow)
            if errors:
                print("Erreurs de validation :")
                for err in errors:
                    print(f"  - {err}")
                sys.exit(1)
            else:
                print("Workflow valide.")
        except Exception as e:
            print(f"Erreur : {e}")
            sys.exit(1)

    elif command == "build-and-verify":
        output = sys.argv[2] if len(sys.argv) >= 3 else "build-and-verify.workflow.json"
        wf = create_build_verify_workflow()
        WorkflowCodec.save(wf, output)
        print(f"Workflow sauvegardé dans {output}")

    else:
        print("Commande inconnue.")
        sys.exit(1)
