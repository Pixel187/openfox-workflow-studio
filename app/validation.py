"""Module de validation partagé : wrapper codec + generator strict.

Purpose: Valider un workflow OpenFox en fusionnant les erreurs structurelles
du codec et les erreurs logiques du generator.
Responsibilities:
  - Appeler workflow_codec.WorkflowCodec.validate (erreurs structurelles)
  - Appeler workflow_generator.validate_workflow (anti-code, reachability, agentId)
  - Fusionner, dédupliquer, séparer les warnings (maxIterations > 50)
Dependencies: workflow_codec, workflow_generator (imports via OPENFOX_ROOT)
Usage examples:
    from app.validation import validate_workflow
    report = validate_workflow(wf_dict)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workflow_codec import WorkflowCodec, WorkflowDefinition
from workflow_generator import validate_workflow as generator_validate


@dataclass
class ValidationReport:
    """Résultat de validation : valide + erreurs + avertissements."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_workflow(wf: dict[str, Any]) -> ValidationReport:
    """Valide un workflow en fusionnant codec + generator.

    DEVIATION DOCUMENTEE : le generator traite maxIterations > 50 comme une
    erreur bloquante ; le Studio le traite comme un warning non bloquant car
    le full-pipeline OpenFox utilise 200 itérations.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Erreurs structurelles du codec
    try:
        definition = WorkflowDefinition.from_dict(wf)
        errors.extend(WorkflowCodec.validate(definition))
    except Exception as exc:  # noqa: BLE001 - le codec peut lever sur structure invalide
        errors.append(f"Structure invalide : {exc}")

    # 2. Erreurs logiques du generator
    try:
        _, generator_errors = generator_validate(wf)
    except Exception as exc:  # noqa: BLE001
        generator_errors = [f"Validation generator impossible : {exc}"]

    # 3. Séparer maxIterations > 50 en warning (déviation documentée)
    for err in generator_errors:
        if "maxIterations > 50" in err:
            warnings.append(err)
        else:
            errors.append(err)

    # 4. Déduplication (codec et generator détectent les mêmes goto)
    seen: set[str] = set()
    deduped: list[str] = []
    for err in errors:
        if err not in seen:
            seen.add(err)
            deduped.append(err)

    return ValidationReport(valid=len(deduped) == 0, errors=deduped, warnings=warnings)