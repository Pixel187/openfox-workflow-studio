"""Routes HTTP de la base d'agents (CRUD complet)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent_base import COLLECTIONS, delete_template, get_template, list_templates, save_template

router = APIRouter(prefix="/api")


class TemplatePayload(BaseModel):
    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1)
    description: str = ""
    collection: str = "general"
    type: str = Field(pattern="^(agent|sub_agent)$")
    phase: str = Field(min_length=1)
    agentId: str = Field(min_length=1)
    subAgentType: str | None = None
    subGroup: str = ""
    prompt: str = Field(min_length=1)
    nudgePrompt: str | None = None


def _validate_collection(collection: str) -> None:
    if collection not in COLLECTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Collection invalide : {collection}. Valeurs : {', '.join(COLLECTIONS)}",
        )


@router.get("/agent-base")
def get_agent_base() -> list[dict[str, Any]]:
    """Retourne la liste des gabarits d'agents."""
    try:
        return list_templates()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/agent-base/{template_id}")
def get_one_template(template_id: str) -> dict[str, Any]:
    """Retourne un gabarit par id."""
    try:
        return get_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Gabarit '{template_id}' introuvable") from exc


@router.post("/agent-base", status_code=201)
def create_template(payload: TemplatePayload) -> dict[str, Any]:
    """Crée un nouveau gabarit."""
    _validate_collection(payload.collection)
    try:
        get_template(payload.id)
        raise HTTPException(status_code=409, detail=f"Gabarit '{payload.id}' existe déjà")
    except KeyError:
        pass
    template = payload.model_dump(exclude_none=True)
    save_template(template)
    return template


@router.put("/agent-base/{template_id}")
def update_template(template_id: str, payload: TemplatePayload) -> dict[str, Any]:
    """Remplace un gabarit existant (l'id du payload doit correspondre)."""
    if payload.id != template_id:
        raise HTTPException(status_code=422, detail="L'id du payload doit correspondre à l'URL")
    _validate_collection(payload.collection)
    try:
        get_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Gabarit '{template_id}' introuvable") from exc
    template = payload.model_dump(exclude_none=True)
    save_template(template)
    return template


@router.delete("/agent-base/{template_id}", status_code=204, response_model=None)
def remove_template(template_id: str) -> None:
    """Supprime un gabarit."""
    try:
        delete_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Gabarit '{template_id}' introuvable") from exc