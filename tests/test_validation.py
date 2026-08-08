"""Tests du module de validation partagé (validation.py)."""

from __future__ import annotations

import sys
from pathlib import Path

# La racine openfox doit être dans sys.path pour importer workflow_codec
# (mécanisme identique à app/__init__.py : réutilisation par import, pas de copie).
OPENFOX_ROOT = Path(__file__).resolve().parents[2]
if str(OPENFOX_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENFOX_ROOT))

from workflow_codec import create_build_verify_workflow

from app.validation import validate_workflow


def test_build_verify_workflow_valid() -> None:
    wf = create_build_verify_workflow().to_dict()
    report = validate_workflow(wf)
    assert report.valid is True
    assert report.errors == []


def test_broken_goto_produces_errors() -> None:
    wf = create_build_verify_workflow().to_dict()
    wf["steps"][0]["transitions"][0]["goto"] = "s99_inexistant"
    report = validate_workflow(wf)
    assert report.valid is False
    assert any("s99_inexistant" in e for e in report.errors)


def test_max_iterations_200_is_warning_not_error() -> None:
    wf = create_build_verify_workflow().to_dict()
    wf["settings"]["maxIterations"] = 200
    report = validate_workflow(wf)
    # DEVIATION DOCUMENTEE : le generator traite >50 comme error, le Studio
    # le traite comme warning non bloquant (full-pipeline utilise 200).
    assert report.valid is True
    assert any("maxIterations" in w for w in report.warnings)


def test_missing_metadata_invalid() -> None:
    report = validate_workflow({"metadata": {}})
    assert report.valid is False
    assert len(report.errors) > 0


def test_errors_deduplicated() -> None:
    wf = create_build_verify_workflow().to_dict()
    wf["steps"][0]["transitions"][0]["goto"] = "s99_inexistant"
    report = validate_workflow(wf)
    # Le même goto est détecté par le codec ET le generator : dédupliqué
    assert len([e for e in report.errors if "s99_inexistant" in e]) == 1