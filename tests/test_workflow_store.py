"""Tests de la couche fichiers workflows (workflow_store.py)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from app.workflow_store import (
    PathTraversalError,
    delete_workflow,
    list_workflows,
    read_workflow,
    resolve_path,
    slugify,
    write_workflow,
)


@pytest.fixture()
def ws_dir(tmp_path: Path) -> Path:
    """Répertoire de travail temporaire pour les tests."""
    return tmp_path


def _sample_workflow() -> dict:
    return {"name": "Test", "steps": [{"id": "s1", "agent": "builder"}]}


def test_slugify_basic() -> None:
    assert slugify("Mon Workflow") == "mon-workflow"


def test_slugify_accents() -> None:
    # Comportement du generator original : l'apostrophe est supprimée sans tiret
    assert slugify("Été à l'île") == "ete-a-lile"


def test_slugify_invalid_chars() -> None:
    assert slugify("Test!! 123") == "test-123"


def test_write_and_read_roundtrip(ws_dir: Path) -> None:
    path = ws_dir / "demo.workflow.json"
    write_workflow(_sample_workflow(), path)
    assert path.exists()
    loaded = read_workflow(path)
    assert loaded["name"] == "Test"
    assert loaded["steps"][0]["id"] == "s1"


def test_write_is_atomic_no_tmp_left(ws_dir: Path) -> None:
    path = ws_dir / "atomic.workflow.json"
    write_workflow(_sample_workflow(), path)
    assert not (ws_dir / "atomic.workflow.json.tmp").exists()


def test_list_workflows(ws_dir: Path) -> None:
    write_workflow(_sample_workflow(), ws_dir / "a.workflow.json")
    write_workflow(_sample_workflow(), ws_dir / "b.workflow.json")
    (ws_dir / "ignore.txt").write_text("x", encoding="utf-8")
    names = [p.name for p in list_workflows(ws_dir)]
    assert names == ["a.workflow.json", "b.workflow.json"]


def test_delete_workflow(ws_dir: Path) -> None:
    path = ws_dir / "del.workflow.json"
    write_workflow(_sample_workflow(), path)
    delete_workflow(path)
    assert not path.exists()


def test_resolve_path_normal(ws_dir: Path) -> None:
    resolved = resolve_path("demo", ws_dir)
    assert resolved == (ws_dir / "demo.workflow.json").resolve()


def test_resolve_path_rejects_dotdot(ws_dir: Path) -> None:
    with pytest.raises(PathTraversalError):
        resolve_path("..\\evil.workflow.json", ws_dir)


def test_resolve_path_rejects_sub_dotdot(ws_dir: Path) -> None:
    with pytest.raises(PathTraversalError):
        resolve_path("sub\\..\\evil.json", ws_dir)


def test_resolve_path_rejects_absolute_windows(ws_dir: Path) -> None:
    with pytest.raises(PathTraversalError):
        resolve_path("C:\\Windows\\evil.json", ws_dir)


def test_lock_conflict(ws_dir: Path) -> None:
    path = ws_dir / "locked.workflow.json"
    lock_path = path.with_suffix(path.suffix + ".lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, f"{os.getpid()}:{time.time()}".encode())
    os.close(fd)
    try:
        with pytest.raises(OSError):
            write_workflow(_sample_workflow(), path, lock=True)
    finally:
        lock_path.unlink(missing_ok=True)


def test_lock_released_after_write(ws_dir: Path) -> None:
    path = ws_dir / "release.workflow.json"
    write_workflow(_sample_workflow(), path, lock=True)
    assert not (path.with_suffix(path.suffix + ".lock")).exists()


def test_orphan_lock_cleaned(ws_dir: Path) -> None:
    path = ws_dir / "orphan.workflow.json"
    lock_path = path.with_suffix(path.suffix + ".lock")
    # pid 99999999 n'existe pas
    lock_path.write_text("99999999:0", encoding="utf-8")
    write_workflow(_sample_workflow(), path, lock=True)
    assert not lock_path.exists()


def test_external_change_detection(ws_dir: Path) -> None:
    path = ws_dir / "ext.workflow.json"
    write_workflow(_sample_workflow(), path)
    before = read_workflow(path)
    # Modification externe : on réécrit le fichier directement
    time.sleep(0.01)
    path.write_text(json.dumps({"name": "Changed", "steps": []}), encoding="utf-8")
    after = read_workflow(path)
    assert before != after