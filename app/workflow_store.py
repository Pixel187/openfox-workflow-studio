"""Couche fichiers workflows : CRUD, verrou par fichier, détection de modification externe.

Purpose: Accès sûr et thread-safe aux fichiers `.workflow.json` dans WS_DIR.
Responsibilities:
  - Lister / lire / écrire / supprimer les workflows
  - Slugifier les noms (kebab-case, translittération des accents)
  - Résoudre les chemins en bloquant le path traversal (Windows-safe)
  - Verrou par fichier (création exclusive O_CREAT|O_EXCL) + nettoyage orphelins
  - Détecter les modifications externes (mtime+size, hash sha256 en backup)
Dependencies: pathlib, os, json, hashlib, time
Usage examples:
    from app.workflow_store import list_workflows, read_workflow, write_workflow
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any


class PathTraversalError(ValueError):
    """Levée quand un identifiant de workflow tente de sortir de WS_DIR."""


class WorkflowLockError(OSError):
    """Levée quand le verrou d'un fichier est déjà acquis."""


def slugify(name: str) -> str:
    """Convertit un nom en identifiant kebab-case (translitère les accents)."""
    wf_id = name.lower().strip()
    wf_id = wf_id.replace(" ", "-")
    for a in "éèêë":
        wf_id = wf_id.replace(a, "e")
    for a in "àâ":
        wf_id = wf_id.replace(a, "a")
    for a in "ùûü":
        wf_id = wf_id.replace(a, "u")
    for a in "ôö":
        wf_id = wf_id.replace(a, "o")
    for a in "îï":
        wf_id = wf_id.replace(a, "i")
    for a in "ç":
        wf_id = wf_id.replace(a, "c")
    wf_id = re.sub(r"[^a-z0-9-]", "", wf_id)
    wf_id = re.sub(r"-+", "-", wf_id).strip("-")
    return wf_id


def resolve_path(workflow_id: str, ws_dir: Path | None = None) -> Path:
    """Résout un identifiant vers un chemin sûr dans WS_DIR.

    Anti path-traversal ROBUSTE :
      1. Rejette tout identifiant contenant des séparateurs de chemin ou `..`
         (contournable autrement sous Windows avec `..\\` ou `C:\\...`).
      2. Résout le chemin complet puis vérifie qu'il reste dans WS_DIR
         (le simple test `Path(id).name == id` est contournable).
    """
    base = (ws_dir or _default_ws_dir()).resolve()
    if ".." in workflow_id or "/" in workflow_id or "\\" in workflow_id:
        raise PathTraversalError(f"Identifiant de chemin refusé : {workflow_id!r}")
    name = (
        workflow_id
        if workflow_id.endswith(".workflow.json")
        else f"{workflow_id}.workflow.json"
    )
    candidate = (base / name).resolve()
    if not candidate.is_relative_to(base):
        raise PathTraversalError(f"Chemin hors de WS_DIR refusé : {workflow_id!r}")
    return candidate


def _default_ws_dir() -> Path:
    from app.config import settings

    return settings.workflows_dir


def list_workflows(ws_dir: Path | None = None) -> list[Path]:
    """Liste les fichiers `*.workflow.json` triés par nom."""
    base = ws_dir or _default_ws_dir()
    if not base.exists():
        return []
    return sorted(base.glob("*.workflow.json"))


def read_workflow(path: Path) -> dict[str, Any]:
    """Lit un workflow JSON (UTF-8)."""
    return json.loads(path.read_text(encoding="utf-8"))


def _pid_exists(pid: int) -> bool:
    """Vérifie si un processus existe (Windows : tasklist, sinon kill 0)."""
    if os.name == "nt":
        try:
            import subprocess

            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock(lock_path: Path) -> None:
    """Acquiert un verrou par création exclusive. Nettoie les orphelins."""
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        # Verrou existant : vérifier s'il est orphelin (pid mort)
        try:
            content = lock_path.read_text(encoding="utf-8")
            pid_str = content.split(":")[0].strip()
            pid = int(pid_str) if pid_str.isdigit() else -1
        except Exception:
            pid = -1
        if pid > 0 and not _pid_exists(pid):
            lock_path.unlink(missing_ok=True)
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        else:
            raise WorkflowLockError(f"Verrou déjà acquis : {lock_path.name}")
    os.write(fd, f"{os.getpid()}:{time.time()}".encode())
    os.close(fd)


def write_workflow(
    workflow: dict[str, Any],
    path: Path,
    lock: bool = False,
) -> None:
    """Écrit un workflow de façon atomique (tmp + os.replace), avec verrou optionnel."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    if lock:
        _acquire_lock(lock_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(workflow, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, path)
    finally:
        if lock:
            lock_path.unlink(missing_ok=True)


def delete_workflow(path: Path) -> None:
    """Supprime un workflow (et son verrou s'il existe)."""
    path.unlink(missing_ok=True)
    path.with_suffix(path.suffix + ".lock").unlink(missing_ok=True)


def file_signature(path: Path) -> tuple[int, int, str]:
    """Signature de fichier : (mtime_ns, size, sha256) pour détection externe."""
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return (stat.st_mtime_ns, stat.st_size, digest)