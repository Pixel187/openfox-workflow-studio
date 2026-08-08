"""Point de terminaison de santé GET /api/health."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    """Retourne l'état de santé de l'application."""
    return {"status": "ok", "app": "workflow-studio"}