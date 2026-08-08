"""Configuration de l'application workflow-studio.

Toutes les valeurs sont externalisées via variables d'environnement / fichier .env.
Aucune valeur en dur (principe AGENTS.md : configuration toujours externalisée).
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application, lisibles depuis .env ou l'environnement."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Client Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral-small3.2"

    # Répertoires de données
    app_data: str = os.environ.get("APPDATA", str(Path.home() / ".config" / "openfox"))
    ws_dir: str = ""

    # Serveur
    port: int = 8765

    @property
    def workflows_dir(self) -> Path:
        """Répertoire des workflows OpenFox : %APPDATA%\\openfox\\workflows."""
        if self.ws_dir:
            return Path(self.ws_dir)
        return Path(self.app_data) / "openfox" / "workflows"


settings = Settings()