"""Point d'entrée uvicorn : python -m uvicorn app.main:app --port 8765."""

from app import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    from app.config import settings

    uvicorn.run(app, host="127.0.0.1", port=settings.port)
