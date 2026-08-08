"""Routes HTTP du catalogue de variables."""

from fastapi import APIRouter

from app.variables import catalog

router = APIRouter(prefix="/api")


@router.get("/variables")
def get_variables() -> dict[str, list[dict[str, object]]]:
    """Retourne le catalogue de variables groupé par catégorie."""
    return catalog()