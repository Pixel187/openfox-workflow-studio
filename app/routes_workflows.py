"""API REST CRUD des workflows (routes_workflows.py).

Purpose: Exposer les workflows OpenFox via une API REST avec ETag/If-Match
pour la détection de conflits et un sidecar de layout (positions canvas).
Responsibilities:
  - GET / : liste résumée des workflows
  - GET /{id} : workflow complet
  - POST / : création (slugify si pas d'id, 409 si existe)
  - PUT /{id} : remplacement (If-Match obligatoire, 412/409/422)
  - DELETE /{id} : suppression (If-Match obligatoire)
  - POST /{id}/validate : validation via module validation
  - GET/PUT /{id}/layout : sidecar positions (ignoré par OpenFox)
Dependencies: workflow_store, validation, config
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response

from app import config
from app.validation import validate_workflow
from app.workflow_store import (
    PathTraversalError,
    WorkflowLockError,
    delete_workflow,
    list_workflows,
    read_workflow,
    resolve_path,
    slugify,
    write_workflow,
)

router = APIRouter(prefix="/api/workflows")


def _ws_dir() -> Path:
    return config.settings.workflows_dir


def _etag_of(content: bytes) -> str:
    return f'"{hashlib.sha256(content).hexdigest()}"'


def _read_with_meta(path: Path) -> tuple[dict[str, Any], str, int]:
    content = path.read_bytes()
    data = json.loads(content.decode("utf-8"))
    return data, _etag_of(content), path.stat().st_mtime_ns


def _summary(data: dict[str, Any], path: Path) -> dict[str, Any]:
    meta = data.get("metadata", {})
    return {
        "id": meta.get("id", path.stem),
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "version": meta.get("version", ""),
        "color": meta.get("color", ""),
        "mtime": path.stat().st_mtime_ns,
        "stepCount": len(data.get("steps", [])),
    }


@router.get("")
def list_all() -> list[dict[str, Any]]:
    """Liste les workflows (résumé)."""
    return [_summary(read_workflow(p), p) for p in list_workflows(_ws_dir())]


@router.get("/{workflow_id}")
def get_one(workflow_id: str) -> Response:
    """Retourne un workflow complet avec ETag."""
    try:
        path = resolve_path(workflow_id, _ws_dir())
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    data, etag, mtime = _read_with_meta(path)
    return Response(
        content=json.dumps(data, ensure_ascii=False),
        media_type="application/json",
        headers={"ETag": etag, "X-MTime": str(mtime)},
    )


@router.post("", status_code=201)
def create(payload: dict[str, Any]) -> Response:
    """Crée un workflow. 409 si l'id existe déjà."""
    meta = payload.get("metadata", {})
    workflow_id = meta.get("id") or slugify(meta.get("name", "workflow"))
    if not workflow_id:
        raise HTTPException(status_code=422, detail="metadata.id ou metadata.name requis")
    try:
        path = resolve_path(workflow_id, _ws_dir())
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Workflow '{workflow_id}' existe déjà")
    payload.setdefault("metadata", {})["id"] = workflow_id
    write_workflow(payload, path, lock=True)
    data, etag, mtime = _read_with_meta(path)
    return Response(
        content=json.dumps(data, ensure_ascii=False),
        media_type="application/json",
        status_code=201,
        headers={"ETag": etag, "X-MTime": str(mtime)},
    )


@router.put("/{workflow_id}")
def update_workflow(
    workflow_id: str,
    payload: dict,
    request: Request,
    if_match: str | None = Header(default=None),
) -> Response:
    """Remplace un workflow (If-Match obligatoire, 409 si modifié ailleurs)."""
    if if_match is None:
        raise HTTPException(status_code=412, detail="If-Match requis")
    try:
        path = resolve_path(workflow_id, _ws_dir())
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    if payload.get("metadata", {}).get("id") != workflow_id:
        raise HTTPException(status_code=422, detail="metadata.id != workflow_id")
    current, current_etag, _ = _read_with_meta(path)
    if if_match != current_etag:
        raise HTTPException(status_code=409, detail="ETag périmé (modifié ailleurs)")
    try:
        write_workflow(payload, path, lock=True)
    except WorkflowLockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    data, etag, mtime = _read_with_meta(path)
    return Response(
        content=json.dumps(data, ensure_ascii=False),
        media_type="application/json",
        headers={"ETag": etag, "X-MTime": str(mtime)},
    )


@router.delete("/{workflow_id}", status_code=204, response_model=None)
def delete_one(workflow_id: str, if_match: str | None = Header(default=None)) -> Response:
    """Supprime un workflow (If-Match obligatoire)."""
    if if_match is None:
        raise HTTPException(status_code=412, detail="If-Match requis")
    try:
        path = resolve_path(workflow_id, _ws_dir())
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    _, current_etag, _ = _read_with_meta(path)
    if if_match != current_etag:
        raise HTTPException(status_code=409, detail="ETag périmé (modifié ailleurs)")
    delete_workflow(path)
    return Response(status_code=204)


@router.post("/{workflow_id}/validate")
def validate_one(workflow_id: str) -> dict[str, Any]:
    """Valide un workflow (codec + generator)."""
    try:
        path = resolve_path(workflow_id, _ws_dir())
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    data = read_workflow(path)
    report = validate_workflow(data)
    return {
        "valid": report.valid,
        "errors": report.errors,
        "warnings": report.warnings,
    }


def _layout_path(workflow_id: str) -> Path:
    try:
        base = _ws_dir().resolve()
        if ".." in workflow_id or "/" in workflow_id or "\\" in workflow_id:
            raise PathTraversalError("Identifiant de chemin refusé")
        return (base / f"{workflow_id}.positions.json").resolve()
    except PathTraversalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{workflow_id}/layout")
def get_layout(workflow_id: str) -> dict[str, Any]:
    """Retourne le sidecar de positions (404 si absent)."""
    path = _layout_path(workflow_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Layout absent")
    return json.loads(path.read_text(encoding="utf-8"))


@router.put("/{workflow_id}/layout")
def put_layout(workflow_id: str, payload: dict) -> dict[str, Any]:
    """Écrit le sidecar de positions."""
    path = _layout_path(workflow_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload