"""Catalogue de variables de template : fusion runtime OpenFox + codec + custom.

Purpose: Fournir au frontend la liste complète des variables utilisables dans
les prompts, groupées par catégorie.
Responsibilities:
  - RUNTIME_VARS : 8 variables officielles injectées par le runtime OpenFox
    (source : executor.ts TEMPLATE_VARIABLES)
  - CODEC_VARS : 9 variables du codec (workflow_codec.TemplateVar)
  - find_template_vars : détection large de {{...}} (y compris custom)
  - catalog : fusion groupée par catégorie avec description + exemple
Dependencies: workflow_codec (import), re
"""

from __future__ import annotations

import re

from workflow_codec import TEMPLATE_VAR_NAMES

RUNTIME_VARS: list[dict[str, object]] = [
    {
        "name": "workdir",
        "category": "Runtime",
        "description": "Répertoire de travail du workflow",
        "example": "C:\\Users\\Home\\openfox\\workflows\\mon-workflow",
    },
    {
        "name": "reason",
        "category": "Runtime",
        "description": "Raison de l'exécution de l'étape courante",
        "example": "Analyser le dossier client",
    },
    {
        "name": "stepOutput",
        "category": "Runtime",
        "description": "Sortie de l'étape précédente",
        "subfields": ["content", "stdout", "stderr", "exitCode"],
        "example": "{{stepOutput.content}}",
    },
    {
        "name": "criteriaCount",
        "category": "Runtime",
        "description": "Nombre de critères de vérification",
        "example": "3",
    },
    {
        "name": "criteriaList",
        "category": "Runtime",
        "description": "Liste des critères de vérification",
        "example": "1. Le document est signé",
    },
    {
        "name": "pendingCount",
        "category": "Runtime",
        "description": "Nombre d'étapes en attente",
        "example": "2",
    },
    {
        "name": "modifiedFiles",
        "category": "Runtime",
        "description": "Fichiers modifiés par l'étape précédente",
        "example": "docs/rapport.md",
    },
]

_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")


def _codec_description(name: str) -> str:
    descriptions = {
        "workdir": "Répertoire de travail du workflow",
        "stepId": "Identifiant de l'étape courante",
        "agentId": "Identifiant de l'agent courant",
        "subAgentType": "Type de sous-agent",
        "sessionId": "Identifiant de session",
        "caseId": "Identifiant de cas/dossier",
        "workflowName": "Nom du workflow",
        "workflowDescription": "Description du workflow",
        "workflowVersion": "Version du workflow",
    }
    return descriptions.get(name, name)


def _codec_example(name: str) -> str:
    return {
        "workdir": "/tmp/workflow",
        "stepId": "step-1",
        "agentId": "builder",
        "subAgentType": "sub_agent",
        "sessionId": "ses_abc123",
        "caseId": "case-42",
        "workflowName": "build-and-verify",
        "workflowDescription": "Build puis vérification",
        "workflowVersion": "1.0.0",
    }.get(name, f"{{{{{name}}}}}")


CODEC_VARS: list[dict[str, object]] = [
    {
        "name": name,
        "category": "Session" if name in ("sessionId", "caseId") else "Workflow",
        "description": _codec_description(name),
        "example": _codec_example(name),
    }
    for name in TEMPLATE_VAR_NAMES
]


def find_template_vars(text: str) -> list[str]:
    """Détecte toutes les variables {{...}} dans un texte (dédupliquées).

    Regex large : accepte toute variable, y compris les variables custom
    inconnues du codec (contrairement à TEMPLATE_PATTERN du codec).
    """
    seen: list[str] = []
    for match in _TEMPLATE_PATTERN.findall(text):
        if match not in seen:
            seen.append(match)
    return seen


def catalog() -> dict[str, list[dict[str, object]]]:
    """Fusionne les variables groupées par catégorie (Runtime / Session / Workflow / Custom)."""
    categories: dict[str, list[dict[str, object]]] = {
        "Runtime": [],
        "Session": [],
        "Workflow": [],
        "Custom": [],
    }
    for var in RUNTIME_VARS:
        categories["Runtime"].append(var)
    for var in CODEC_VARS:
        categories[var["category"]].append(var)  # type: ignore[index]
    return categories