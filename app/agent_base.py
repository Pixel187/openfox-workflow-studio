"""Base d'agents : bibliothèque locale de gabarits de prompts.

Purpose: Fournir des gabarits de prompts réutilisables (dérivés du PDF OpenFox
et des besoins métier) pour construire des étapes de workflow.
Responsibilities:
  - Lire/écrire/supprimer des gabarits JSON dans workflow-studio/agent_base/
  - Seed de gabarits par collection (general, codage, redaction, juridique)
Dependencies: pathlib, json
Usage examples:
    from app.agent_base import list_templates, get_template, save_template
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

AGENT_BASE_DIR = Path(__file__).resolve().parents[1] / "agent_base"

COLLECTIONS = ("general", "codage", "redaction", "juridique")

_SEED_TEMPLATES: list[dict[str, Any]] = [
    # ── Collection general (transversal) ──────────────────────────────
    {
        "id": "planner",
        "name": "Planner",
        "description": "Planifie le travail : découpe l'objectif en étapes.",
        "collection": "general",
        "type": "agent",
        "phase": "planning",
        "agentId": "builder",
        "subGroup": "planning",
        "prompt": (
            "Planifie le travail demandé. Dépôt : {{workdir}}.\n\n"
            "1. Analyse l'objectif et la spécification.\n"
            "2. Décompose en étapes indépendantes, chacune avec un livrable mesurable.\n"
            "3. Pour chaque étape, cite les références Zotero pertinentes ([@cle]).\n"
            "4. Écris le plan dans un fichier markdown.\n"
            "5. step_done()"
        ),
        "nudgePrompt": "Sois précis : chaque étape doit être actionnable sans ambiguïté.",
    },
    {
        "id": "builder-drafter",
        "name": "Builder-Drafter",
        "description": "Exécute le travail : rédige ou construit le livrable.",
        "collection": "general",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": (
            "Exécute le travail demandé. Dépôt : {{workdir}}.\n\n"
            "1. Lis les fichiers sources et la spécification.\n"
            "2. Rédige le contenu en français, en citant les sources ([@cle]).\n"
            "3. Écris le livrable dans le fichier prévu.\n"
            "4. session_metadata(action=\"add\", key=\"criteria\", description=\"<critère>\", status=\"completed\")\n"
            "5. step_done()"
        ),
        "nudgePrompt": "Garde les prompts déterministes et vérifiables.",
    },
    {
        "id": "verifier",
        "name": "Verifier",
        "description": "Vérifie le travail : contrôle les critères et la qualité.",
        "collection": "general",
        "type": "sub_agent",
        "phase": "verification",
        "agentId": "builder",
        "subAgentType": "verifier",
        "subGroup": "verify",
        "prompt": (
            "Vérifie le travail produit. Dépôt : {{workdir}}.\n\n"
            "1. session_metadata(action=\"get\", key=\"criteria\")\n"
            "2. Lis le livrable produit et compare-le aux critères.\n"
            "3. Pour chaque écart, enregistre un constat :\n"
            "   session_metadata(action=\"update\", key=\"verifierFindings\", id=\"<id>\", status=\"<passed|failed>\", detail=\"<constat>\")\n"
            "4. return_value(content=\"Vérification terminée : <résumé>\")"
        ),
        "nudgePrompt": "Signale tout constat objectif, sans exagération.",
    },
    # ── codage (développement) ────────────────────────────────────────
    {
        "id": "architecte",
        "name": "Architecte",
        "description": "Découpe la spécification en structure technique.",
        "collection": "codage",
        "type": "agent",
        "phase": "planning",
        "agentId": "builder",
        "subGroup": "planning",
        "prompt": (
            "Conçois l'architecture technique. Dépôt : {{workdir}}.\n\n"
            "1. Lis la spécification et identifie les composants.\n"
            "2. Définis les modules, leurs responsabilités et leurs dépendances.\n"
            "3. Précise les choix techniques (langage, librairies, patterns).\n"
            "4. Écris le document d'architecture en markdown.\n"
            "5. step_done()"
        ),
        "nudgePrompt": "Respecte les principes SOLID et la séparation des préoccupations.",
    },
    {
        "id": "implementateur",
        "name": "Implementateur",
        "description": "Écrit le code d'une fonctionnalité avec ses tests.",
        "collection": "codage",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": (
            "Implémente la fonctionnalité demandée. Dépôt : {{workdir}}.\n\n"
            "1. Lis la spécification et le code existant.\n"
            "2. Écris le code en suivant les conventions du projet.\n"
            "3. Ajoute les tests unitaires couvrant le happy path et les cas limites.\n"
            "4. Vérifie que les tests passent.\n"
            "5. step_done()"
        ),
        "nudgePrompt": "Code propre, typé, sans anti-patterns. Ne refactore pas hors périmètre.",
    },
    {
        "id": "debugger",
        "name": "Debugger",
        "description": "Trouve la cause racine d'une erreur et la corrige.",
        "collection": "codage",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": (
            "Corrige l'erreur signalée. Dépôt : {{workdir}}.\n\n"
            "1. Reproduis l'erreur et lis la trace complète.\n"
            "2. Formule au moins 3 hypothèses de cause racine.\n"
            "3. Vérifie chaque hypothèse avant de modifier le code.\n"
            "4. Applique le correctif minimal et relance les tests.\n"
            "5. step_done()"
        ),
        "nudgePrompt": "Corrige la cause racine, jamais le symptôme. Pas de correctifs au hasard.",
    },
    {
        "id": "refactorer",
        "name": "Refactorer",
        "description": "Améliore la structure du code sans changer le comportement.",
        "collection": "codage",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": (
            "Refactore le code ciblé. Dépôt : {{workdir}}.\n\n"
            "1. Identifie les zones à améliorer (duplication, complexité, couplage).\n"
            "2. Vérifie que les tests existants couvrent le comportement.\n"
            "3. Refactore par petites étapes, en gardant les tests verts.\n"
            "4. step_done()"
        ),
        "nudgePrompt": "Refactoring incrémental uniquement. Ne change jamais le comportement.",
    },
    {
        "id": "testeur",
        "name": "Testeur",
        "description": "Écrit des tests unitaires et d'intégration complets.",
        "collection": "codage",
        "type": "sub_agent",
        "phase": "verification",
        "agentId": "builder",
        "subAgentType": "verifier",
        "subGroup": "verify",
        "prompt": (
            "Teste le code produit. Dépôt : {{workdir}}.\n\n"
            "1. Lis le code et identifie les fonctions publiques.\n"
            "2. Écris des tests : happy path, cas limites, scénarios d'échec.\n"
            "3. Vérifie la couverture et signale les zones non testées.\n"
            "4. return_value(content=\"Rapport de tests : <résumé>\")"
        ),
        "nudgePrompt": "Ne t'arrête pas au happy path : couvre les cas limites et les échecs.",
    },
    {
        "id": "reviewer",
        "name": "Reviewer",
        "description": "Revue de code : qualité, sécurité, patterns.",
        "collection": "codage",
        "type": "sub_agent",
        "phase": "review",
        "agentId": "builder",
        "subAgentType": "code_reviewer",
        "subGroup": "review",
        "prompt": (
            "Revue le code du dépôt. Dépôt : {{workdir}}.\n\n"
            "1. Lis les fichiers modifiés et leurs tests.\n"
            "2. Vérifie : qualité, sécurité, performance, conventions.\n"
            "3. Signale chaque problème avec sa gravité et une correction proposée.\n"
            "4. return_value(content=\"Revue terminée : <résumé>\")"
        ),
        "nudgePrompt": "Signale les vrais problèmes, pas le style personnel.",
    },
    {
        "id": "documenteur",
        "name": "Documenteur",
        "description": "Génère la documentation (README, API, guides).",
        "collection": "codage",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": (
            "Rédige la documentation. Dépôt : {{workdir}}.\n\n"
            "1. Lis le code et identifie les fonctionnalités publiques.\n"
            "2. Rédige le README : installation, usage, exemples.\n"
            "3. Documente les API et les commandes.\n"
            "4. step_done()"
        ),
        "nudgePrompt": "Documentation concise, orientée usage, avec exemples réels.",
    },
    # ── rédaction (livres, documents) ─────────────────────────────────
    {
        "id": "planificateur-livre",
        "name": "Planificateur de livre",
        "description": "Structure le plan d'un livre : chapitres et mots-clés.",
        "collection": "redaction",
        "type": "agent",
        "phase": "planning",
        "agentId": "builder",
        "subGroup": "planning",
        "prompt": (
            "Planifie le livre demandé. Dépôt : {{workdir}}.\n\n"
            "1. Analyse le sujet et le public cible.\n"
            "2. Décompose en chapitres avec un objectif par chapitre.\n"
            "3. Pour chaque chapitre, liste les mots-clés et sujets à couvrir.\n"
            "4. Écris le plan dans un fichier markdown.\n"
            "5. step_done()"
        ),
        "nudgePrompt": "Chaque chapitre doit avoir un livrable mesurable et un fil conducteur clair.",
    },
    {
        "id": "redacteur",
        "name": "Rédacteur",
        "description": "Rédige en langage courant, ton adapté au public.",
        "collection": "redaction",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": (
            "Rédige le contenu demandé. Dépôt : {{workdir}}.\n\n"
            "1. Lis le plan et les sources fournies.\n"
            "2. Rédige en français, en langage courant et naturel.\n"
            "3. Structure en paragraphes avec des transitions fluides.\n"
            "4. Écris le livrable dans le fichier prévu.\n"
            "5. step_done()"
        ),
        "nudgePrompt": "Style naturel, sans jargon inutile. Évite les tournures artificielles.",
    },
    {
        "id": "relecteur",
        "name": "Relecteur",
        "description": "Corrige grammaire, style et cohérence du texte.",
        "collection": "redaction",
        "type": "sub_agent",
        "phase": "verification",
        "agentId": "builder",
        "subAgentType": "verifier",
        "subGroup": "verify",
        "prompt": (
            "Relis le texte produit. Dépôt : {{workdir}}.\n\n"
            "1. Lis le texte et identifie les fautes de grammaire et d'orthographe.\n"
            "2. Vérifie la cohérence du style et des transitions.\n"
            "3. Signale les passages artificiels ou répétitifs.\n"
            "4. return_value(content=\"Relecture terminée : <résumé>\")"
        ),
        "nudgePrompt": "Signale les vrais problèmes de style, pas les préférences personnelles.",
    },
    {
        "id": "humanizer",
        "name": "Humanizer",
        "description": "Nettoie le style IA : rend le texte naturel et authentique.",
        "collection": "redaction",
        "type": "sub_agent",
        "phase": "review",
        "agentId": "builder",
        "subAgentType": "code_reviewer",
        "subGroup": "review",
        "prompt": (
            "Humanise le texte produit. Dépôt : {{workdir}}.\n\n"
            "1. Identifie les tournures typiques de l'IA (transitions creuses, formules génériques).\n"
            "2. Réécris les passages pour un style naturel et authentique.\n"
            "3. Supprime les affirmations exagérées non étayées.\n"
            "4. return_value(content=\"Texte humanisé : <résumé>\")"
        ),
        "nudgePrompt": "Préserve le sens et les faits. Ne supprime que le style artificiel.",
    },
    # ── juridique (droit luxembourgeois) ──────────────────────────────
    {
        "id": "analyste-dossier",
        "name": "Analyste de dossier",
        "description": "Analyse un dossier et identifie les points juridiques.",
        "collection": "juridique",
        "type": "agent",
        "phase": "planning",
        "agentId": "builder",
        "subGroup": "planning",
        "prompt": (
            "Analyse le dossier juridique. Dépôt : {{workdir}}.\n\n"
            "1. Lis les documents du dossier.\n"
            "2. Identifie les points juridiques pertinents (sociétés, fonds, fiscalité, RGPD).\n"
            "3. Cite les sources officielles (Legilux, EUR-Lex, CSSF).\n"
            "4. Distingue clairement faits / hypothèses / avis.\n"
            "5. Écris l'analyse en markdown.\n"
            "6. step_done()"
        ),
        "nudgePrompt": "Ne jamais inventer de références légales. Préciser la version applicable des textes.",
    },
    {
        "id": "redacteur-juridique",
        "name": "Rédacteur juridique",
        "description": "Rédige des documents juridiques avec citations officielles.",
        "collection": "juridique",
        "type": "agent",
        "phase": "build",
        "agentId": "builder",
        "subGroup": "build",
        "prompt": (
            "Rédige le document juridique demandé. Dépôt : {{workdir}}.\n\n"
            "1. Lis l'analyse et les sources fournies.\n"
            "2. Rédige en français juridique précis, en citant les sources officielles.\n"
            "3. Distingue faits, hypothèses et avis.\n"
            "4. Mentionne les modifications récentes importantes.\n"
            "5. Écris le document dans le fichier prévu.\n"
            "6. step_done()"
        ),
        "nudgePrompt": "Citations exactes (Legilux, EUR-Lex). Jamais de référence inventée.",
    },
    {
        "id": "verificateur-conformite",
        "name": "Vérificateur de conformité",
        "description": "Contrôle la conformité AML/KYC, RGPD et réglementaire.",
        "collection": "juridique",
        "type": "sub_agent",
        "phase": "verification",
        "agentId": "builder",
        "subAgentType": "verifier",
        "subGroup": "verify",
        "prompt": (
            "Vérifie la conformité du dossier. Dépôt : {{workdir}}.\n\n"
            "1. Lis le dossier et les exigences réglementaires applicables.\n"
            "2. Contrôle : AML/KYC (Loi LBC/FT), RGPD, règles sectorielles.\n"
            "3. Pour chaque écart, enregistre un constat :\n"
            "   session_metadata(action=\"update\", key=\"verifierFindings\", id=\"<id>\", status=\"<passed|failed>\", detail=\"<constat>\")\n"
            "4. return_value(content=\"Contrôle de conformité : <résumé>\")"
        ),
        "nudgePrompt": "Signale tout écart objectif, avec la source réglementaire correspondante.",
    },
]


def _ensure_dir() -> Path:
    AGENT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    return AGENT_BASE_DIR


def seed_if_empty() -> None:
    """Crée les gabarits seed si le dossier est vide (premier lancement)."""
    d = _ensure_dir()
    if not list(d.glob("*.json")):
        for template in _SEED_TEMPLATES:
            save_template(template)


def list_templates() -> list[dict[str, Any]]:
    """Liste les gabarits JSON (triés par id)."""
    seed_if_empty()
    result: list[dict[str, Any]] = []
    for path in sorted(AGENT_BASE_DIR.glob("*.json")):
        result.append(json.loads(path.read_text(encoding="utf-8")))
    return result


def get_template(template_id: str) -> dict[str, Any]:
    """Retourne un gabarit par id. Lève KeyError si absent."""
    seed_if_empty()
    path = AGENT_BASE_DIR / f"{template_id}.json"
    if not path.exists():
        raise KeyError(f"Gabarit '{template_id}' introuvable")
    return json.loads(path.read_text(encoding="utf-8"))


def save_template(template: dict[str, Any]) -> None:
    """Écrit ou remplace un gabarit."""
    _ensure_dir()
    template_id = template["id"]
    path = AGENT_BASE_DIR / f"{template_id}.json"
    path.write_text(
        json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def delete_template(template_id: str) -> None:
    """Supprime un gabarit. Lève KeyError si absent."""
    seed_if_empty()
    path = AGENT_BASE_DIR / f"{template_id}.json"
    if not path.exists():
        raise KeyError(f"Gabarit '{template_id}' introuvable")
    path.unlink()