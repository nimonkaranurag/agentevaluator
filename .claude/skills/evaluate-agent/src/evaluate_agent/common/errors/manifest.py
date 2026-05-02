"""
Typed exceptions raised by the manifest loader.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.manifest.api_version import (
    API_VERSION_KEY,
    CURRENT_API_VERSION,
    SUPPORTED_API_VERSIONS,
)
from pydantic import ValidationError

_SKILL_ROOT = Path(__file__).resolve().parents[4]
_ONBOARDING_GUIDE = _SKILL_ROOT / "SKILL.md"


class ManifestError(Exception):
    pass


class ManifestNotFoundError(ManifestError):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Manifest not found at: {path}\n"
            f"To proceed:\n"
            f"  (1) Confirm that an agent.yaml exists at the expected path (typically the working directory).\n"
            f"  (2) Re-invoke the skill with the correct path, or consult the skill onboarding guide at: {_ONBOARDING_GUIDE}."
        )


class ManifestSyntaxError(ManifestError):
    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(
            f"Manifest YAML is malformed at: {path}\n"
            f"Parser detail: {detail}\n"
            f"To proceed:\n"
            f"  (1) Open the file and fix the YAML at the location indicated in the parser detail.\n"
            f"  (2) Re-run the validator to confirm the manifest parses before retrying any downstream step."
        )


class ManifestMissingApiVersionError(ManifestError):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Manifest at {path} does not declare the "
            f"required {API_VERSION_KEY!r} field.\n"
            f"To proceed:\n"
            f"  (1) Add `{API_VERSION_KEY}: "
            f"{CURRENT_API_VERSION}` as the first line of "
            f"the manifest. The field pins the manifest to "
            f"a known schema version so future schema "
            f"changes cannot silently re-bind older "
            f"manifests.\n"
            f"  (2) Re-run the loader. The authoritative "
            f"set of accepted versions is "
            f"src/evaluate_agent/manifest/api_version/"
            f"literal.py."
        )


class ManifestUnsupportedApiVersionError(ManifestError):
    def __init__(
        self,
        *,
        path: Path,
        declared: object,
    ) -> None:
        self.path = path
        self.declared = declared
        super().__init__(
            f"Manifest at {path} declares "
            f"{API_VERSION_KEY}={declared!r}, which is not "
            f"in the supported set "
            f"{sorted(SUPPORTED_API_VERSIONS)}.\n"
            f"To proceed:\n"
            f"  (1) If the manifest was authored against "
            f"this skill release, set "
            f"`{API_VERSION_KEY}: {CURRENT_API_VERSION}` "
            f"and re-run the loader.\n"
            f"  (2) If the manifest was authored against a "
            f"newer schema version, upgrade the "
            f"evaluate-agent skill to a release that "
            f"supports it; the authoritative supported set "
            f"is src/evaluate_agent/manifest/api_version/"
            f"literal.py."
        )


class ManifestValidationError(ManifestError):
    def __init__(
        self,
        path: Path,
        cause: ValidationError,
    ) -> None:
        self.path = path
        self.cause = cause
        super().__init__(self._format(path, cause))

    @staticmethod
    def _format(path: Path, ve: ValidationError) -> str:
        lines = [
            f"Manifest failed schema validation at: {path} ({ve.error_count()} violation(s) below)."
        ]
        for err in ve.errors():
            location = (
                ".".join(str(p) for p in err["loc"])
                or "<root>"
            )
            lines.append(f"  - {location}: {err['msg']}")
        lines.append(
            "To proceed: fix every violation listed above and re-run the validator. "
            "The authoritative schema is src/evaluate_agent/manifest/schema.py."
        )
        return "\n".join(lines)


class ManifestDiscoveryRootError(ManifestError):
    def __init__(self, root: Path) -> None:
        self.root = root
        super().__init__(
            f"Manifest discovery root is not a directory: {root}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path exists and is a directory (not a file, not a missing path).\n"
            f"  (2) Re-invoke discovery with a directory path, or consult the skill onboarding guide at: {_ONBOARDING_GUIDE}."
        )


__all__ = [
    "ManifestDiscoveryRootError",
    "ManifestError",
    "ManifestMissingApiVersionError",
    "ManifestNotFoundError",
    "ManifestSyntaxError",
    "ManifestUnsupportedApiVersionError",
    "ManifestValidationError",
]
