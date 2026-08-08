# Workflow Studio

Éditeur visuel de workflows pour OpenFox : construisez des pipelines d'agents IA
(planification → exécution → vérification) par glisser-déposer, avec une banque
de gabarits de prompts, un assistant IA et l'export des workflows.

## Architecture

```
Frontend React (Vite + TypeScript + React Flow)
        │  /api (proxy Vite)
        ▼
Backend FastAPI (Python)
        │
        ├── workflow_store.py   — persistance JSON des workflows
        ├── validation.py       — validation structurelle + anti-code
        ├── agent_base.py       — banque de gabarits de prompts (4 collections)
        ├── agent_proposer.py   — assistant IA (propose / apply / discard)
        └── ollama_client.py    — client Ollama
```

Le studio embarque deux modules du runtime OpenFox (copiés à la racine du dépôt) :

- `workflow_codec.py` — codec des définitions de workflow
- `workflow_generator.py` — validation des workflows (anti-code, reachability)

## Prérequis

- Python 3.11+
- Node.js 18+
- Ollama (pour l'assistant IA, optionnel)

## Installation

```bat
install.bat
```

Crée le venv Python, installe les dépendances backend (`requirements.txt`)
et frontend (`web/package.json`).

## Démarrage

```bat
start.bat
```

Lance le backend FastAPI (port 8765) et le frontend Vite (port 5173), puis
ouvre le navigateur sur http://localhost:5173.

## Tests

```bat
:: Backend (pytest)
.venv\Scripts\python.exe -m pytest

:: Frontend (vitest)
cd web
npm test
```

## Structure

```
app/                 — backend FastAPI
  routes_*.py        — endpoints REST
  agent_base.py      — banque d'agents (seed + CRUD)
  workflow_store.py  — persistance
web/src/             — frontend React
  components/        — palette, canvas, inspecteur, assistant
  store/             — état du workflow (Zustand)
  lib/               — sérialisation, gabarits
tests/               — tests backend (pytest)
web/src/__tests__/   — tests frontend (vitest)
```

## Banque d'agents

Les gabarits de prompts sont organisés en 4 collections :

| Collection | Contenu |
|---|---|
| `general` | Planner, Builder-Drafter, Verifier |
| `codage` | Architecte, Implementateur, Debugger, Refactorer, Testeur, Reviewer, Documenteur |
| `redaction` | Planificateur de livre, Rédacteur, Relecteur, Humanizer |
| `juridique` | Analyste de dossier, Rédacteur juridique, Vérificateur de conformité |

Les gabarits sont stockés dans `agent_base/*.json` (générés au premier lancement,
non versionnés) et gérables depuis l'interface (création, édition, suppression).

## Configuration

Variables d'environnement (ou fichier `.env`) :

| Variable | Défaut | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://192.168.178.10:11434` | URL du serveur Ollama |
| `OLLAMA_MODEL` | `mistral-small3.2` | Modèle par défaut |
| `WS_DIR` | `%APPDATA%\openfox\workflows` | Répertoire des workflows |
| `PORT` | `8765` | Port du backend |