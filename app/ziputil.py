"""Utilitaire zip avec défense ZIP-SLIP.

Purpose: Extraire des archives zip en toute sécurité.
Responsibilities:
  - safe_extractall : rejette tout membre absolu ou contenant `..`
Dependencies: zipfile, os
Usage examples:
    from app.ziputil import safe_extractall
    safe_extractall(zf, target_dir)
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path


def safe_extractall(zf: zipfile.ZipFile, target_dir: Path) -> None:
    """Extrait une archive en rejetant les membres dangereux (zip-slip).

    Chaque membre est vérifié : ni chemin absolu, ni composant `..`.
    """
    for member in zf.infolist():
        name = member.filename
        if os.path.isabs(name):
            raise ValueError(f"Chemin absolu refusé dans l'archive : {name}")
        if ".." in name.split("/"):
            raise ValueError(f"Chemin `..` refusé dans l'archive : {name}")
    zf.extractall(target_dir)