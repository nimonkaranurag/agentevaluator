"""
Load a CaseNarrative from a JSON file with typed-error mapping.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluate_agent.common.errors.case_narrative import (
    CaseNarrativeNotFoundError,
    CaseNarrativeSyntaxError,
    CaseNarrativeValidationError,
)
from pydantic import ValidationError

from .schema import CaseNarrative


def load_case_narrative(path: Path) -> CaseNarrative:
    if not path.is_file():
        raise CaseNarrativeNotFoundError(path)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CaseNarrativeSyntaxError(
            path=path, parse_error=str(exc)
        ) from exc

    if not isinstance(raw, dict):
        raise CaseNarrativeSyntaxError(
            path=path,
            parse_error=(
                f"expected a JSON object at the top "
                f"level; got {type(raw).__name__}"
            ),
        )

    try:
        return CaseNarrative.model_validate(raw)
    except ValidationError as exc:
        raise CaseNarrativeValidationError(
            path=path, validation_error=exc
        ) from exc


__all__ = ["load_case_narrative"]
