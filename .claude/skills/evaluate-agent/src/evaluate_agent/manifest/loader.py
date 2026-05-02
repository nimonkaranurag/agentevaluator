"""
Load and validate an agent manifest from disk.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from evaluate_agent.common.errors.manifest import (
    ManifestMissingApiVersionError,
    ManifestNotFoundError,
    ManifestSyntaxError,
    ManifestUnsupportedApiVersionError,
    ManifestValidationError,
)
from pydantic import ValidationError

from .api_version import (
    API_VERSION_KEY,
    SUPPORTED_API_VERSIONS,
)
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

    # apiVersion gating runs before model_validate so the failure
    # surfaces as a typed exception with an actionable recovery
    # procedure rather than as a Pydantic literal-mismatch buried
    # inside a ValidationError stack. The two failure modes are
    # distinct because they imply different fixes — missing means
    # "add the field", unsupported means "this build doesn't know
    # this version" — and the typed exceptions encode that split.
    if API_VERSION_KEY not in raw:
        raise ManifestMissingApiVersionError(path)
    declared_version = raw[API_VERSION_KEY]
    if declared_version not in SUPPORTED_API_VERSIONS:
        raise ManifestUnsupportedApiVersionError(
            path=path,
            declared=declared_version,
        )

    try:
        return AgentManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestValidationError(path, exc) from exc


__all__ = ["load_manifest"]
