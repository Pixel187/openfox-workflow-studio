"""Routes d'export : fichier natif + bundle zip.

Purpose: Exporter les workflows OpenFox (fichier natif ou bundle zip).
Responsibilities:
  - GET /api/workflows/{id}/export : fichier .workflow.json natif
  - GET /api/export/bundle : zip (workflows/ + agent_base/ + manifest.json + README)
Dependencies: workflow_store, agent_base, zipfile
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app import agent_base, config
from app.workflow_store import (
    PathTraversalError,
    list_workflows,
    read_workflow,
    resolve_path,
)

router = APIRouter(prefix="/api")


@router.get("/workflows/{workflow_id}/export")
def export_native(workflow_id: str) -> FileResponse:
    """Retourne le fichier .workflow.json natif."""
    try:
        path = resolve_path(workflow_id, config.settings.workflows_dir)
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"{workflow_id}.workflow.json",
    )


@router.get("/export/bundle")
def export_bundle() -> StreamingResponse:
    """Crée un bundle zip : workflows + gabarits + manifest + README."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        workflows_dir = config.settings.workflows_dir
        workflow_ids: list[str] = []
        for wf_path in list_workflows(workflows_dir):
            name = wf_path.name
            workflow_ids.append(name[: -len(".workflow.json")])
            zf.writestr(f"workflows/{name}", wf_path.read_bytes())

        agent_base.seed_if_empty()
        for template_path in sorted(agent_base.AGENT_BASE_DIR.glob("*.json")):
            zf.writestr(f"agent_base/{template_path.name}", template_path.read_bytes())

        manifest = {
            "exporter": "workflow-studio",
            "version": 1,
            "date": datetime.now(timezone.utc).isoformat(),
            "workflow_ids": workflow_ids,
            "schemaVersion": "1.0",
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

        readme = (
            "# Bundle workflow-studio\n\n"
            "## Contenu\n"
            "- `workflows/` : fichiers .workflow.json natifs\n"
            "- `agent_base/` : gabarits de prompts JSON\n"
            "- `manifest.json` : métadonnées du bundle (schemaVersion 1.0)\n\n"
            "## Ré-import\n"
            "1. Copier les fichiers `workflows/*.workflow.json` dans le répertoire "
            "des workflows OpenFox (`%APPDATA%\\openfox\\workflows`).\n"
            "2. Copier les gabarits `agent_base/*.json` dans le dossier agent_base "
            "du studio.\n"
        )
        zf.writestr("README-export.md", readme)

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=workflow-studio-export.zip"},
    )