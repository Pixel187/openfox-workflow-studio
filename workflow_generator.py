#!/usr/bin/env python3
"""
OpenFox Workflow Generator — Assistant interactif
==================================================
Génère des workflows OpenFox valides via Ollama,
en suivant les standards et bonnes pratiques identifiés.

Usage : python workflow_generator.py
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ── CONSTANTES ──────────────────────────────────────────────────────────────

APP_DATA = Path(os.environ.get("APPDATA", ""))
WORKFLOWS_DIR = APP_DATA / "openfox" / "workflows"
BEST_PRACTICES_FILE = (
    Path.home() / "openfox" / "Livre_IA_et_Droit" / "BONNES_PRATIQUES_WORKFLOW.md"
)
OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
DEFAULT_MODEL = "mistral-small3.2"

COLORS_HEX = [
    "#3b82f6",
    "#8b5cf6",
    "#ef4444",
    "#10b981",
    "#f59e0b",
    "#ec4899",
    "#06b6d4",
    "#84cc16",
]


def c(text, code=36):
    """Colorisation terminal."""
    return f"\033[{code}m{text}\033[0m"


# ── RESSOURCES ──────────────────────────────────────────────────────────────


def load_best_practices():
    """Charge les bonnes pratiques depuis le fichier .md."""
    if BEST_PRACTICES_FILE.exists():
        text = BEST_PRACTICES_FILE.read_text(encoding="utf-8")
        return text[:4000]  # limite pour le prompt
    return ""


def list_existing_workflows():
    """Liste les workflows existants."""
    if not WORKFLOWS_DIR.exists():
        return []
    return sorted(WORKFLOWS_DIR.glob("*.workflow.json"))


def extract_json(text):
    """Extrait le premier objet JSON d'une réponse texte."""
    # bloc ```json ... ```
    m = re.search(r"```(?:json)?\s*\n?(.*?)(?:\n|\r\n)?```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # premier { ... dernier }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ── OLLAMA ──────────────────────────────────────────────────────────────────


def ask_ollama(system_prompt, user_prompt, model=DEFAULT_MODEL):
    """Appelle l'API chat d'Ollama. Retourne le texte ou None."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
        "stream": False,
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  {c('ERREUR HTTP', 91)}: {e.code} — {body[:200]}")
    except Exception as e:
        print(f"  {c('ERREUR', 91)}: {e}")
    return None


# ── PROMPTS ─────────────────────────────────────────────────────────────────


def prompt_gabarit():
    """Retourne le gabarit JSON injecté dans le prompt système."""
    return {
        "metadata": {
            "id": "mon_workflow",
            "name": "Mon Workflow",
            "description": "Description courte",
            "version": "1.0.0",
            "color": "#3b82f6",
        },
        "entryStep": "s1",
        "settings": {"maxIterations": 50},
        "steps": [
            {
                "id": "s1",
                "name": "Premiere etape",
                "type": "agent",
                "phase": "build",
                "agentId": "builder",
                "transitions": [{"when": {"type": "always"}, "goto": "s2"}],
                "prompt": "Ta mission…",
                "subGroup": "planning",
            },
            {
                "id": "s2",
                "name": "Deuxieme etape",
                "type": "sub_agent",
                "phase": "build",
                "agentId": "builder",
                "subAgentType": "verifier",
                "transitions": [{"when": {"type": "always"}, "goto": "$done"}],
                "prompt": "Tu es le redacteur…",
                "subGroup": "build",
            },
        ],
        "startCondition": {"type": "always"},
    }


def build_system_prompt():
    """Prompt système = règles + gabarit + contraintes."""
    bp = load_best_practices()

    return f"""Tu es un expert en génération de workflows OpenFox.
Tu produis UNIQUEMENT du JSON valide, sans texte avant ni après.

RÈGLES STRICTES — IMPÉRATIF :

1. STRUCTURE : suis EXACTEMENT la structure du gabarit fourni.
   — metadata {{
       "id": "identifiant-kebab-case",
       "name": "Nom lisible",
       "description": "Courte description",
       "version": "1.0.0",
       "color": "#3b82f6"  // un hex parmi: {" ".join(COLORS_HEX)}
     }}
   — entryStep: "s1"
   — settings: {{"maxIterations": 50}} (ne pas dépasser 50)
   — steps: tableau d'étapes
   — startCondition: {{"type": "always"}}

2. AGENT : TOUTES les étapes doivent avoir "agentId": "builder".
   "planner" est INTERDIT — il n'a pas les outils d'écriture.

3. TRANSITIONS : chaque transition = {{"when": {{"type": "always"}}, "goto": "sX"}}
   — le goto doit pointer vers une étape EXISTANTE ou "$done"
   — pour les conditions : {{"when": {{"type": "step_result", "result": "success"}}, "goto": "sX"}}
   — le dernier goto d'une chaîne sans boucle doit être "$done"

4. PROMPTS — contraintes des prompts d'étape :
   — TOUS les prompts en français
   — ZÉRO code (pas de Python, JS, batch, subprocess, os.system, etc.)
   — Pour les workflows de rédaction :
     * l'étape de rédaction doit lire `_progress.md` pour savoir quelle section écrire
     * doit mettre à jour `_progress.md` après chaque section
     * doit enrichir `GLOSSAIRE.md` avec les nouveaux termes
     * doit écrire section par section (5-10 paragraphes max par génération)
     * ne JAMAIS exiger "5000 mots par chapitre" comme sortie unique
   — Directifs, style impératif, commençant par "Tu es le…"

5. TYPES D'ÉTAPE :
   — "type": "agent" → étape standard avec outils d'écriture
   — "type": "sub_agent" → sous-agent contexte frais, nécessite "subAgentType"
     * "subAgentType": "verifier" → agent de vérification
     * "subAgentType": "code_reviewer" → agent de review final

6. PHASES / SUBGROUPS :
   — phases: "build" | "verification" | "review"
   — subGroups: "planning" | "research" | "bibliography" | "build" | "verify" | "review"

7. NOMS DE FICHIERS : utiliser le format chapitre_01.md (padding zéro, lowercase)

BONNES PRATIQUES DU PROJET (référence) :
{bp[:3000] if bp else "(non disponibles)"}

GABARIT DE BASE :
{json.dumps(prompt_gabarit(), indent=2, ensure_ascii=False)}

RÉPONDS UNIQUEMENT AVEC LE JSON BRUT. AUCUN TEXTE AVANT NI APRÈS."""


def build_user_prompt(requirements):
    """Prompt utilisateur à partir des réponses de la session interactive."""
    return f"""Génère un workflow OpenFox complet pour le besoin suivant :

{requirements}

Rappel : JSON brut uniquement, agentId:"builder" pour toutes les étapes,
prompts en français sans code, transitions cohérentes."""


# ── VALIDATION ──────────────────────────────────────────────────────────────


def validate_workflow(wf):
    """Retourne (ok: bool, erreurs: list[str])."""
    err = []

    # 1. Champs racine
    for k in ("metadata", "entryStep", "settings", "steps", "startCondition"):
        if k not in wf:
            err.append(f"Champ racine manquant : {k}")

    if not wf.get("steps"):
        err.append("Aucune étape définie")
        return False, err

    # 2. metadata
    meta = wf.get("metadata", {})
    for k in ("id", "name", "description", "version"):
        if k not in meta:
            err.append(f"metadata.{k} manquant")
    color = meta.get("color", "")
    if color and not re.match(r"^#[0-9a-fA-F]{6}$", color):
        err.append(f"Couleur invalide : {color}")

    # 3. settings
    mi = wf.get("settings", {}).get("maxIterations", 50)
    if mi > 50:
        err.append(f"maxIterations > 50 ({mi}) — risque de boucle")

    steps = wf["steps"]
    ids = [s["id"] for s in steps]

    # 4. entryStep
    if wf.get("entryStep") not in ids:
        err.append(f"entryStep '{wf.get('entryStep')}' introuvable dans steps")

    # 5. IDs uniques
    if len(ids) != len(set(ids)):
        for i in set(ids):
            if ids.count(i) > 1:
                err.append(f"ID en double : {i}")

    # 6. Vérification de chaque étape
    for s in steps:
        sid = s["id"]
        agent = s.get("agentId", "")
        if agent == "planner":
            err.append(f"[{sid}] agentId 'planner' interdit — utiliser 'builder'")
        elif agent != "builder":
            err.append(f"[{sid}] agentId '{agent}' non standard (attendu: 'builder')")

        # type + subAgentType
        stype = s.get("type", "")
        if stype == "sub_agent" and not s.get("subAgentType"):
            err.append(f"[{sid}] sub_agent sans subAgentType")

        # transitions
        for t in s.get("transitions", []):
            g = t.get("goto", "")
            if not g:
                g = t.get("when", {}).get("goto", "")
            if g and g not in ids and g != "$done":
                err.append(f"[{sid}] goto '{g}' ne correspond à aucune étape")

        # prompts → anti-code (signaux forts de génération de code)
        prompt_text = s.get("prompt", "") + s.get("nudgePrompt", "")

        # Regex anti-code : on utilise des regex pour éviter les faux positifs
        # .json ne doit pas déclencher .js  →  lookahead (?!on)
        code_patterns = [
            (r"\.py(?:\b|$)", ".py"),
            (r"\.js(?!on)", ".js"),
            (r"\bsubprocess\b", "subprocess"),
            (r"os\.system", "os.system"),
            (r"exec\s*\(", "exec("),
            (r"Invoke-WebRequest", "Invoke-WebRequest"),
            (r"cat\s+>", "cat >"),
            (r"<<\s*['\"]?EOC", "heredoc"),
            (r"python3\s+-c", "python3 -c"),
            (r"bash\s+-c", "bash -c"),
            (r"sh\s+-c", "sh -c"),
        ]
        for p, label in code_patterns:
            if re.search(p, prompt_text, re.IGNORECASE):
                err.append(f"[{sid}] motif suspect '{label}' dans le prompt")

        # Signaux plus faibles (peuvent être dans des instructions négatives)
        if re.search(r"\bimport\s+", prompt_text) and re.search(
            r"\b(?:os|subprocess)\b", prompt_text
        ):
            err.append(f"[{sid}] import de module système dans le prompt")

    # 7. Cohérence globale : test de chaîne simple
    visited = set()
    stack = [wf.get("entryStep")]
    while stack:
        sid = stack.pop()
        if sid in visited:
            continue
        if sid == "$done":
            continue
        visited.add(sid)
        for s in steps:
            if s["id"] == sid:
                for t in s.get("transitions", []):
                    g = t.get("goto", "") or t.get("when", {}).get("goto", "")
                    if g and g not in visited:
                        stack.append(g)
                break

    unreachable = [i for i in ids if i not in visited and i != wf.get("entryStep")]
    if unreachable:
        err.append(f"Étapes inatteignables depuis entryStep : {unreachable}")

    return len(err) == 0, err


# ── SAUVEGARDE ──────────────────────────────────────────────────────────────


def save_workflow(wf, wf_id):
    """Sauvegarde le workflow dans openfox/workflows/."""
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    path = WORKFLOWS_DIR / f"{wf_id}.workflow.json"

    if path.exists():
        print(f"\n  {c('⚠', 33)} {path.name} existe déjà.")
        ok = input(f"  {c('?', 33)} Écraser ? (o/N) : ").strip().lower()
        if ok != "o":
            return None

    path.write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


# ── SESSION INTERACTIVE ─────────────────────────────────────────────────────


def ask(question, default=None):
    """Pose une question et retourne la réponse."""
    suffixe = f" (défaut: {default})" if default else ""
    return input(f"  {c('?', 33)} {question}{suffixe} : {c('', 0)}").strip() or (
        default or ""
    )


def interactive_session():
    """Collecte les besoins via dialogue interactif."""
    print(f"\n{'=' * 56}")
    print(f"  {c('GÉNÉRATEUR DE WORKFLOW OPENFOX', 36)}")
    print(f"{'=' * 56}\n")

    name = ask("Nom du workflow")
    while not name:
        name = ask("Nom (requis)")

    wf_id = name.lower()
    wf_id = wf_id.replace(" ", "-")
    for a in "éèêë":
        wf_id = wf_id.replace(a, "e")
    for a in "àâ":
        wf_id = wf_id.replace(a, "a")
    for a in "ùûü":
        wf_id = wf_id.replace(a, "u")
    for a in "ôö":
        wf_id = wf_id.replace(a, "o")
    for a in "îï":
        wf_id = wf_id.replace(a, "i")
    wf_id = re.sub(r"[^a-z0-9-]", "", wf_id)

    desc = ask("Description courte")

    print(f"\n  {c('Objectif principal :', 36)}")
    print("    1) Rédaction")
    print("    2) Recherche / Sourcing")
    print("    3) Relecture / Vérification")
    print("    4) Mixte")
    obj = ask("Choix (1-4)", "4")
    obj_map = {"1": "redaction", "2": "recherche", "3": "relecture", "4": "mixte"}
    main_obj = obj_map.get(obj, "mixte")

    steps_str = ask("Nombre d'étapes (2-8)", "4")
    try:
        n_steps = max(2, min(8, int(steps_str)))
    except ValueError:
        n_steps = 4

    print(f"\n  {c('Modèle Ollama :', 36)}")
    print("    1) mistral-small3.2 (recommandé)")
    print("    2) qwen3.6:latest (puissant, risque crash)")
    print("    3) qwen2.5:32b-instruct")
    m_choice = ask("Choix (1-3)", "1")
    model_map = {
        "1": "mistral-small3.2",
        "2": "qwen3.6:latest",
        "3": "qwen2.5:32b-instruct",
    }
    model = model_map.get(m_choice, "mistral-small3.2")

    print(f"\n  {c('Spécificités (optionnel) :', 36)}")
    specifics = ask(">", "")
    print('  Ex: "ajouter verification Zotero", "utiliser SearXNG"')

    default_dir = str(Path.home() / "openfox" / wf_id)
    workdir = ask("Répertoire de travail", default_dir)

    # Construire la spécification structurée
    req = f"""NOM : {name}
ID : {wf_id}
DESCRIPTION : {desc}
OBJECTIF : {main_obj}
NOMBRE_ETAPES : {n_steps}
MODÈLE : {model}
RÉPERTOIRE : {workdir}
SPÉCIFICITÉS : {specifics or "(aucune)"}
TYPE_AGENT : builder (obligatoire)
LANGUE : fr (prompts en français)
ANTI_CODE : true (aucun code dans les prompts)
"""

    if main_obj in ("redaction", "mixte"):
        req += "MEMOIRE_EXTERNE : true (_progress.md + GLOSSAIRE.md)\nSECTION_PAR_SECTION : true\n"

    return req, wf_id, model


# ── BOUCLE PRINCIPALE ──────────────────────────────────────────────────────


def main():
    try:
        requirements, wf_id, model = interactive_session()
    except (EOFError, KeyboardInterrupt):
        print(f"\n  {c('Interrompu.', 90)}")
        return

    # Génération
    n_essai = 0
    while n_essai < 3:
        n_essai += 1
        print(f"\n  {c('Génération…', 36)} (essai {n_essai}/3, modèle: {model})")

        response = ask_ollama(
            build_system_prompt(),
            build_user_prompt(
                requirements
                + (
                    f"\nTENTATIVE PRÉCÉDENTE — erreurs à corriger :\n{requirements}"
                    if n_essai > 1
                    else ""
                )
            ),
            model=model,
        )

        if not response:
            print(
                f"  {c('Pas de réponse Ollama.', 91)} Vérifie que le modèle est disponible."
            )
            return

        wf = extract_json(response)
        if not wf:
            print(f"  {c('JSON invalide.', 91)} Réponse:")
            for l in response.strip()[:600].split("\n")[:8]:
                print(f"    | {l}")
            continue

        ok, errors = validate_workflow(wf)
        if not ok:
            print(f"  {c('Validation échouée', 91)}:")
            for e in errors[:8]:
                print(f"    {c('✗', 91)} {e}")
            if len(errors) > 8:
                print(f"    … et {len(errors) - 8} autre(s)")
            # Ajouter les erreurs à la req pour le prochain essai
            requirements += "\nERREURS À CORRIGER :\n" + "\n".join(errors[:5])
            continue

        # Succès
        print(f"\n  {c('✓ Workflow valide', 92)}")
        break
    else:
        print(f"\n  {c('Échec après 3 essais.', 91)}")
        return

    # Aperçu + boucle de confirmation/régénération
    while True:
        print(f"\n{'─' * 56}")
        print(f"  {c('APERÇU', 36)}")
        print(f"{'─' * 56}")
        print(f"  Nom      : {wf['metadata']['name']}")
        print(f"  ID       : {wf['metadata']['id']}")
        print(f"  Étapes   : {len(wf['steps'])}")
        for s in wf["steps"]:
            targets = [t.get("goto", "?") for t in s.get("transitions", [])]
            sub = f" [{s.get('subAgentType', '')}]" if s.get("subAgentType") else ""
            print(f"    {s['id']}{sub} → {', '.join(targets)}")
        print(f"{'─' * 56}")

        print(f"\n{c('JSON :', 90)}")
        print(json.dumps(wf, indent=2, ensure_ascii=False))
        print()

        confirm = (
            input(f"  {c('?', 33)} Sauvegarder ? (O/n/r pour régénérer) : ")
            .strip()
            .lower()
        )
        if confirm == "r":
            modifs = ask("Instructions de modification pour la régénération")
            requirements += f"\nMODIFICATIONS : {modifs}"
            # Régénérer sans refaire l'interview
            n_essai = 0
            while n_essai < 3:
                n_essai += 1
                print(f"\n  {c('Régénération…', 36)} (essai {n_essai}/3)")
                response = ask_ollama(
                    build_system_prompt(),
                    build_user_prompt(requirements),
                    model=model,
                )
                if not response:
                    break
                new_wf = extract_json(response)
                if not new_wf:
                    continue
                ok, errors = validate_workflow(new_wf)
                if not ok:
                    print(f"  {c('Validation échouée', 91)}:")
                    for e in errors[:8]:
                        print(f"    {c('✗', 91)} {e}")
                    requirements += "\n" + "\n".join(errors[:5])
                    continue
                wf = new_wf
                print(f"\n  {c('✓ Régénéré', 92)}")
                break
            else:
                print(f"  {c('Échec de la régénération.', 91)}")
                break
            continue  # retour à l'affichage
        elif confirm == "n":
            print(f"  {c('Annulé.', 90)}")
            return
        else:
            # Sauvegarde
            path = save_workflow(wf, wf_id)
            if not path:
                continue  # écrasement annulé, on reste dans la boucle
            print(f"\n  {c('✓ Sauvegardé', 92)}  {path}")
            print(f"\n  Redémarre OpenFox puis lance le workflow '{wf_id}'.")
            break

    # Lister les workflows existants
    existants = list_existing_workflows()
    print(f"\n  Workflows dans {WORKFLOWS_DIR} :")
    for f in existants:
        print(f"    {f.name}")


if __name__ == "__main__":
    main()
