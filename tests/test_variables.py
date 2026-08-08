"""Tests du catalogue de variables de template (variables.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.variables import (
    CODEC_VARS,
    RUNTIME_VARS,
    catalog,
    find_template_vars,
)


def test_runtime_vars_count() -> None:
    # Le plan annonce "8" mais ne liste que 7 noms ; la liste explicite prime.
    assert len(RUNTIME_VARS) == 7


def test_runtime_vars_names() -> None:
    names = {v["name"] for v in RUNTIME_VARS}
    assert names == {
        "workdir",
        "reason",
        "stepOutput",
        "criteriaCount",
        "criteriaList",
        "pendingCount",
        "modifiedFiles",
    }


def test_step_output_has_subfields() -> None:
    step_output = next(v for v in RUNTIME_VARS if v["name"] == "stepOutput")
    assert set(step_output["subfields"]) == {"content", "stdout", "stderr", "exitCode"}


def test_codec_vars_count() -> None:
    assert len(CODEC_VARS) == 9


def test_codec_vars_names() -> None:
    names = {v["name"] for v in CODEC_VARS}
    assert names == {
        "workdir",
        "stepId",
        "agentId",
        "subAgentType",
        "sessionId",
        "caseId",
        "workflowName",
        "workflowDescription",
        "workflowVersion",
    }


def test_find_template_vars_dedupe() -> None:
    text = "Utilise {{workdir}} et encore {{workdir}} puis {{stepId}}"
    assert find_template_vars(text) == ["workdir", "stepId"]


def test_find_custom_var() -> None:
    assert find_template_vars("Projet {{nom_projet}}") == ["nom_projet"]


def test_find_template_vars_empty() -> None:
    assert find_template_vars("Aucune variable ici") == []


def test_catalog_has_categories() -> None:
    cat = catalog()
    assert "Runtime" in cat
    assert "Session" in cat
    assert "Workflow" in cat
    assert "Custom" in cat


def test_catalog_total_count() -> None:
    # 7 runtime + 9 codec = 16 (le plan annonce 17 mais ne liste que 7 runtime)
    total = sum(len(items) for items in catalog().values())
    assert total >= 16


def test_catalog_contains_workdir() -> None:
    all_items = [item for items in catalog().values() for item in items]
    assert any(item["name"] == "workdir" for item in all_items)


def test_api_variables_returns_200() -> None:
    client = TestClient(app)
    response = client.get("/api/variables")
    assert response.status_code == 200
    payload = response.json()
    assert "Runtime" in payload
    assert "Custom" in payload