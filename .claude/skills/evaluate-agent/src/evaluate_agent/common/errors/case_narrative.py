"""
Typed exceptions raised by the case-narrative loader and renderer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

if TYPE_CHECKING:
    from evaluate_agent.case_narrative.citation_validator import (
        NarrativeCitationFailure,
    )

_SKILL_ROOT = Path(__file__).resolve().parents[4]
_ONBOARDING_GUIDE = _SKILL_ROOT / "SKILL.md"


class CaseNarrativeError(Exception):
    pass


class CaseNarrativeNotFoundError(CaseNarrativeError):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Case narrative not found at: {path}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path matches the file "
            f"the synthesis step wrote (one JSON file "
            f"per case, named after the case_id).\n"
            f"  (2) If the narrative was never "
            f"persisted, write the narrative JSON to "
            f"the expected path and re-invoke the "
            f"validator or renderer.\n"
            f"  (3) The narrative schema lives at "
            f"src/evaluate_agent/case_narrative/"
            f"schema.py; see {_ONBOARDING_GUIDE} for "
            f"the synthesis contract."
        )


class CaseNarrativeSyntaxError(CaseNarrativeError):
    def __init__(
        self,
        *,
        path: Path,
        parse_error: str,
    ) -> None:
        self.path = path
        self.parse_error = parse_error
        super().__init__(
            f"Case narrative at {path} is not valid "
            f"JSON.\n"
            f"Parser detail: {parse_error}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was written "
            f"verbatim from the synthesis step's output "
            f"(no truncation, no shell interpolation).\n"
            f"  (2) Re-emit the narrative as a single "
            f"JSON object whose top-level shape matches "
            f"CaseNarrative (case_id, summary, "
            f"observations) and overwrite the file.\n"
            f"  (3) Re-invoke the validator or renderer "
            f"once the file parses as JSON."
        )


class CaseNarrativeValidationError(CaseNarrativeError):
    def __init__(
        self,
        *,
        path: Path,
        validation_error: ValidationError,
    ) -> None:
        self.path = path
        self.validation_error = validation_error
        super().__init__(
            self._format(path, validation_error)
        )

    @staticmethod
    def _format(path: Path, ve: ValidationError) -> str:
        lines = [
            f"Case narrative at {path} failed schema "
            f"validation ({ve.error_count()} "
            f"violation(s) below).",
        ]
        for err in ve.errors():
            location = (
                ".".join(str(p) for p in err["loc"])
                or "<root>"
            )
            lines.append(f"  - {location}: {err['msg']}")
        lines.append(
            "To proceed: fix every violation listed "
            "above and re-invoke the validator. The "
            "authoritative schema lives at "
            "src/evaluate_agent/case_narrative/"
            "schema.py."
        )
        return "\n".join(lines)


class NarrativeCaseMismatchError(CaseNarrativeError):
    def __init__(
        self,
        *,
        narrative_case_id: str,
        score_case_id: str,
    ) -> None:
        self.narrative_case_id = narrative_case_id
        self.score_case_id = score_case_id
        super().__init__(
            f"Case narrative is bound to case_id "
            f"{narrative_case_id!r} but the score it "
            f"was rendered against is for case_id "
            f"{score_case_id!r}.\n"
            f"To proceed:\n"
            f"  (1) Confirm the narrative file was "
            f"written for the same case as the score. "
            f"A narrative for one case must never be "
            f"embedded in the report of a different "
            f"case.\n"
            f"  (2) Either supply the narrative for "
            f"case {score_case_id!r}, or render the "
            f"score for case "
            f"{narrative_case_id!r} (whichever the "
            f"orchestrator intended)."
        )


class NarrativeUnknownCaseIdsError(CaseNarrativeError):
    def __init__(
        self,
        *,
        unknown_case_ids: tuple[str, ...],
        declared_case_ids: tuple[str, ...],
    ) -> None:
        if not unknown_case_ids:
            raise ValueError(
                "NarrativeUnknownCaseIdsError requires "
                "at least one unknown case id; an empty "
                "tuple indicates every supplied narrative "
                "matches a declared case id and the "
                "renderer should not raise."
            )
        self.unknown_case_ids = unknown_case_ids
        self.declared_case_ids = declared_case_ids
        super().__init__(
            f"Narratives were supplied for "
            f"{len(unknown_case_ids)} case id(s) the "
            f"agent score does not declare: "
            f"{list(unknown_case_ids)}.\n"
            f"Declared case ids: "
            f"{list(declared_case_ids)}.\n"
            f"To proceed:\n"
            f"  (1) Confirm the narratives directory "
            f"holds files for the same cases the "
            f"score covers. The most common cause is "
            f"reusing narratives from an earlier run "
            f"of a different manifest.\n"
            f"  (2) Drop the unknown narratives or "
            f"supply narratives only for declared "
            f"case ids, then re-invoke the renderer."
        )


class NarrativeCitationsUnresolvedError(CaseNarrativeError):
    def __init__(
        self,
        *,
        case_id: str,
        case_dir: Path,
        failures: tuple["NarrativeCitationFailure", ...],
    ) -> None:
        if not failures:
            raise ValueError(
                "NarrativeCitationsUnresolvedError "
                "requires at least one failure; an "
                "empty failure tuple indicates the "
                "narrative is grounded and the renderer "
                "should not raise."
            )
        self.case_id = case_id
        self.case_dir = case_dir
        self.failures = failures
        super().__init__(
            self._format(case_id, case_dir, failures)
        )

    @staticmethod
    def _format(
        case_id: str,
        case_dir: Path,
        failures: tuple["NarrativeCitationFailure", ...],
    ) -> str:
        lines = [
            f"{len(failures)} narrative citation(s) "
            f"for case {case_id!r} did not resolve "
            f"under the bound case directory "
            f"{case_dir}:",
        ]
        for index, failure in enumerate(failures, start=1):
            lines.append(
                f"  ({index}) "
                f"{failure.narrative_path}: "
                f"{failure.artifact_path} "
                f"({failure.failure_reason})"
            )
        lines.append(
            "To proceed:\n"
            "  (1) For every "
            "path_does_not_exist failure: confirm "
            "the cited artifact still lives at the "
            "named path under the case directory. "
            "If it was moved, re-emit the narrative "
            "with the corrected path. If it was "
            "deleted, regenerate the artifact (re-"
            "run open_agent.py for the case) before "
            "re-emitting the narrative.\n"
            "  (2) For every "
            "path_outside_case_directory failure: "
            "the narrative cited an artifact from a "
            "different case directory, which is "
            "never permitted. Re-emit the "
            "narrative citing only artifacts under "
            f"{case_dir}.\n"
            "  (3) Re-invoke the renderer once "
            "every citation resolves to a real file "
            "under the bound case directory."
        )
        return "\n".join(lines)


__all__ = [
    "CaseNarrativeError",
    "CaseNarrativeNotFoundError",
    "CaseNarrativeSyntaxError",
    "CaseNarrativeValidationError",
    "NarrativeCaseMismatchError",
    "NarrativeCitationsUnresolvedError",
    "NarrativeUnknownCaseIdsError",
]
