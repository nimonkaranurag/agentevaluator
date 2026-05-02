"""
Verify every citation inside a CaseNarrative resolves under the bound case directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from evaluate_agent.common.errors.case_narrative import (
    NarrativeCaseMismatchError,
    NarrativeCitationsUnresolvedError,
)
from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.scoring import CaseScore
from pydantic import Field

from .schema import CaseNarrative, NarrativeCitation

NarrativeCitationFailureReason = Literal[
    "path_does_not_exist",
    "path_outside_case_directory",
]


class NarrativeCitationFailure(StrictFrozen):
    narrative_path: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Dotted JSON path locating the failing "
                "citation inside the narrative. "
                "Example: observations[2].citations[0]."
                "artifact_path."
            ),
        ),
    ]
    artifact_path: Annotated[
        Path,
        Field(
            description=(
                "Path the citation pointed at and that "
                "did not satisfy the structural integrity "
                "check."
            ),
        ),
    ]
    failure_reason: Annotated[
        NarrativeCitationFailureReason,
        Field(
            description=(
                "Why the citation is invalid. "
                "path_does_not_exist: the path does not "
                "resolve to a regular file on disk. "
                "path_outside_case_directory: the path "
                "resolves to a real file but lives "
                "outside the case directory the "
                "narrative is bound to."
            ),
        ),
    ]


class NarrativeCitationValidationResult(StrictFrozen):
    failures: Annotated[
        tuple[NarrativeCitationFailure, ...],
        Field(
            description=(
                "One entry per citation that failed the "
                "structural integrity check. Empty when "
                "every citation in the narrative resolves "
                "to a real file under the bound case "
                "directory."
            ),
        ),
    ]

    @property
    def is_valid(self) -> bool:
        return not self.failures


def validate_narrative_citations(
    narrative: CaseNarrative,
    *,
    case_dir: Path,
) -> NarrativeCitationValidationResult:
    resolved_case_dir = case_dir.resolve()
    failures: list[NarrativeCitationFailure] = []
    for obs_index, observation in enumerate(
        narrative.observations
    ):
        for cit_index, citation in enumerate(
            observation.citations
        ):
            failure = _check_citation(
                citation=citation,
                narrative_path=(
                    f"observations[{obs_index}]"
                    f".citations[{cit_index}]"
                    f".artifact_path"
                ),
                resolved_case_dir=resolved_case_dir,
            )
            if failure is not None:
                failures.append(failure)
    return NarrativeCitationValidationResult(
        failures=tuple(failures),
    )


def verify_narrative_against_score(
    narrative: CaseNarrative,
    *,
    score: CaseScore,
) -> None:
    if narrative.case_id != score.case_id:
        raise NarrativeCaseMismatchError(
            narrative_case_id=narrative.case_id,
            score_case_id=score.case_id,
        )
    result = validate_narrative_citations(
        narrative, case_dir=score.case_dir
    )
    if not result.is_valid:
        raise NarrativeCitationsUnresolvedError(
            case_id=score.case_id,
            case_dir=score.case_dir,
            failures=result.failures,
        )


def _check_citation(
    *,
    citation: NarrativeCitation,
    narrative_path: str,
    resolved_case_dir: Path,
) -> NarrativeCitationFailure | None:
    candidate = citation.artifact_path
    if not candidate.is_file():
        return NarrativeCitationFailure(
            narrative_path=narrative_path,
            artifact_path=candidate,
            failure_reason="path_does_not_exist",
        )
    resolved = candidate.resolve()
    if not _path_is_under(resolved, resolved_case_dir):
        return NarrativeCitationFailure(
            narrative_path=narrative_path,
            artifact_path=candidate,
            failure_reason=("path_outside_case_directory"),
        )
    return None


def _path_is_under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


__all__ = [
    "NarrativeCitationFailure",
    "NarrativeCitationFailureReason",
    "NarrativeCitationValidationResult",
    "validate_narrative_citations",
    "verify_narrative_against_score",
]
