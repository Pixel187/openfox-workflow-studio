"""Endpoints propose/apply de l'agent Ollama (routes_agent.py).

Purpose: Proposer des modifications de workflow via Ollama, les afficher en diff,
et ne les appliquer qu'après approbation explicite (porte « Proposer → Approuver »).
Responsibilities:
  - GET /api/ollama/models : liste des modèles disponibles
  - POST /api/agent/propose : génère une proposition (stockée en mémoire, TTL 1h)
  - POST /api/agent/apply : applique une proposition approuvée (ETag check + verrou)
  - POST /api/agent/discard : rejette une proposition
Dependencies: ollama_client, agent_proposer, validation, workflow_store, config
Usage examples:
    POST /api/agent/propose
    {"workflow_id": "demo", "scope": "workflow", "instruction": "Ajoute une étape"}

Note sur la persistance : les propositions sont éphémères (dict module-level).
TTL 1h, perdues au redémarrage — comportement documenté et accepté dans le plan.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import config
from app.agent_proposer import AgentProposer
from app.fake_proposer import FakeProposer
from app.ollama_client import OllamaClient
from app.validation import validate_workflow
from app.workflow_store import (
    PathTraversalError,
    WorkflowLockError,
    read_workflow,
    resolve_path,
    write_workflow,
)

router = APIRouter(prefix="/api")

# Propositions éphémères en mémoire : {proposal_id: {...}}.
# TTL 1h ; perdues au restart (documenté et accepté — pas de DB).
_PROPOSALS: dict[str, dict[str, Any]] = {}
_PROPOSAL_TTL_S = 3600
_lock = asyncio.Lock()

_proposer = FakeProposer() if config.settings.fake_proposer else AgentProposer()
_ollama = OllamaClient()


def _ws_dir():
    return config.settings.workflows_dir


def _etag_of(content: bytes) -> str:
    return f'"{hashlib.sha256(content).hexdigest()}"'


def _read_with_etag(path) -> tuple[dict[str, Any], str]:
    content = path.read_bytes()
    data = json.loads(content.decode("utf-8"))
    return data, _etag_of(content)


class ProposeRequest(BaseModel):
    workflow_id: str
    scope: str = Field(pattern="^(workflow|step|prompt)$")
    step_id: str | None = None
    prompt_only: bool | None = None
    instruction: str
    model: str | None = None


class ApplyRequest(BaseModel):
    proposal_id: str


class DiscardRequest(BaseModel):
    proposal_id: str


def _resolve(workflow_id: str):
    try:
        return resolve_path(workflow_id, _ws_dir())
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ollama/models")
async def list_models() -> dict[str, Any]:
    """Liste les modèles Ollama disponibles (proxie ollama_client)."""
    try:
        models = _ollama.list_models()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"models": models, "default_model": config.settings.ollama_model}


@router.post("/agent/propose")
async def propose(req: ProposeRequest) -> dict[str, Any]:
    """Génère une proposition (scope workflow/step/prompt), ne rien écrit."""
    path = _resolve(req.workflow_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    workflow, etag = _read_with_etag(path)

    try:
        result = _proposer.propose(
            workflow,
            scope=req.scope,
            instruction=req.instruction,
            step_id=req.step_id,
            model=req.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not result.success and req.model and req.model != config.settings.ollama_model:
        result = _proposer.propose(
            workflow,
            scope=req.scope,
            instruction=req.instruction,
            step_id=req.step_id,
            model=config.settings.ollama_model,
        )
        fallback_used = True
    else:
        fallback_used = False

    if not result.success:
        status = 422
        parts = [result.error] if result.error else []
        parts.extend(result.validation_errors)
        detail = "; ".join(parts) if parts else "Proposition invalide"
        raise HTTPException(status_code=status, detail=detail)

    proposal_id = uuid.uuid4().hex
    async with _lock:
        _purge_expired()
        _PROPOSALS[proposal_id] = {
            "workflow_id": req.workflow_id,
            "etag": etag,
            "proposed": result.proposed,
            "scope": req.scope,
            "step_id": req.step_id,
            "created_at": time.time(),
            "preserves_vars": result.preserves_vars,
            "lost_vars": result.lost_vars,
            "original_vars": result.original_vars,
        }

    report = validate_workflow(result.proposed)
    return {
        "proposal_id": proposal_id,
        "proposed": result.proposed,
        "diff": result.diff,
        "validation": {
            "valid": report.valid,
            "errors": report.errors,
            "warnings": report.warnings,
        },
        "preserves_vars": result.preserves_vars,
        "lost_vars": result.lost_vars,
        "fallback_used": fallback_used,
        "fallback_model": config.settings.ollama_model if fallback_used else None,
    }


@router.post("/agent/apply")
async def apply(req: ApplyRequest) -> dict[str, Any]:
    """Applique une proposition approuvée. Écrit uniquement si le fichier
    n'a pas changé depuis le propose (ETag check) et que la proposition est
    encore valide (validation re-exécutée)."""
    async with _lock:
        proposal = _get_proposal(req.proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Proposition inconnue ou expirée")
        workflow_id = proposal["workflow_id"]
        etag_at_propose = proposal["etag"]
        proposed = proposal["proposed"]

        if not proposal["preserves_vars"]:
            raise HTTPException(
                status_code=400,
                detail="La proposition supprime des variables {{...}} — application bloquée : "
                + ", ".join(proposal["lost_vars"]),
            )

        # ETag check : le fichier a-t-il changé depuis le propose ?
        path = _resolve(workflow_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Workflow introuvable")
        _, current_etag = _read_with_etag(path)
        if current_etag != etag_at_propose:
            raise HTTPException(status_code=409, detail="Fichier modifié ailleurs depuis la proposition")

        # Validation re-exécutée avant écriture
        report = validate_workflow(proposed)
        if not report.valid:
            raise HTTPException(status_code=422, detail="; ".join(report.errors))

        try:
            write_workflow(proposed, path, lock=True)
        except WorkflowLockError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        del _PROPOSALS[req.proposal_id]

    data, etag = _read_with_etag(path)
    return {"workflow": data, "etag": etag}


@router.post("/agent/discard", status_code=204, response_model=None)
async def discard(req: DiscardRequest) -> None:
    """Rejette une proposition (ne rien écrit)."""
    async with _lock:
        if req.proposal_id not in _PROPOSALS:
            raise HTTPException(status_code=404, detail="Proposition inconnue ou expirée")
        del _PROPOSALS[req.proposal_id]


def _purge_expired() -> None:
    now = time.time()
    expired = [pid for pid, p in _PROPOSALS.items() if now - p["created_at"] > _PROPOSAL_TTL_S]
    for pid in expired:
        del _PROPOSALS[pid]


def _get_proposal(proposal_id: str) -> dict[str, Any] | None:
    proposal = _PROPOSALS.get(proposal_id)
    if proposal is None:
        return None
    if time.time() - proposal["created_at"] > _PROPOSAL_TTL_S:
        del _PROPOSALS[proposal_id]
        return None
    return proposal
