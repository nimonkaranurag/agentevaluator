"""
Load and validate an agent manifest from disk.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from evaluate_agent.common.errors.manifest import (
    ManifestNotFoundError,
    ManifestSyntaxError,
    ManifestValidationError,
)
from pydantic import ValidationError

from .schema import AgentManifest


def load_manifest(path: Path) -> AgentManifest:
    if not path.is_file():
        raise ManifestNotFoundError(path)

    try:
        raw = yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
    except yaml.YAMLError as exc:
        raise ManifestSyntaxError(path, str(exc)) from exc

    if not isinstance(raw, dict):
        raise ManifestSyntaxError(
            path,
            "expected a YAML mapping at the top level",
        )

    try:
        return AgentManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestValidationError(path, exc) from exc


__all__ = ["load_manifest"]
