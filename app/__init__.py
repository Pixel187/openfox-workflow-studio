"""Factory de l'application FastAPI workflow-studio.

Sépare la construction de l'application (testable) de l'entrée uvicorn.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Le studio vit dans C:\Users\Home\openfox\workflow-studio\app\ donc parents[2] = racine openfox.
# On ajoute la racine au sys.path pour importer workflow_codec / workflow_generator
# par import (réutilisation, pas de copie) — mécanisme documenté dans le plan (todo 4).
OPENFOX_ROOT = Path(__file__).resolve().parents[2]
if str(OPENFOX_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENFOX_ROOT))

from app.health import router as health_router
from app.routes_agent import router as agent_router
from app.routes_agent_base import router as agent_base_router
from app.routes_export import router as export_router
from app.routes_variables import router as variables_router
from app.routes_workflows import router as workflows_router


def create_app() -> FastAPI:
    """Construit et configure l'application FastAPI."""
    app = FastAPI(title="workflow-studio", version="0.1.0")

    # CORS : autorise le proxy Vite en développement
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(variables_router)
    app.include_router(workflows_router)
    app.include_router(agent_base_router)
    app.include_router(export_router)
    app.include_router(agent_router)
    return app


app = create_app()