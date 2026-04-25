"""
Verify every citation inside a score record resolves on disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from ..scoring import (
    AgentScore,
    AssertionFailed,
    AssertionPassed,
    CaseScore,
)

CitedArtifactKind = Literal["file", "directory"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CitationValidationFailure(_Strict):
    score_path: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Dotted JSON path locating the failing "
                "citation inside the score record. "
                "Example: "
                "case_scores[0].outcomes[2]."
                "evidence.artifact_path."
            ),
        ),
    ]
    artifact_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the citation pointed at "
                "and that did not resolve on disk."
            ),
        ),
    ]
    expected_kind: Annotated[
        CitedArtifactKind,
        Field(
            description=(
                "Whether the citation expected the path "
                "to be a regular file or a directory."
            ),
        ),
    ]


class CitationValidationResult(_Strict):
    failures: Annotated[
        tuple[CitationValidationFailure, ...],
        Field(
            description=(
                "One entry per citation that did not "
                "resolve on disk. Empty when every "
                "citation in the score resolves."
            ),
        ),
    ]

    @property
    def is_valid(self) -> bool:
        return not self.failures


def validate_citations(
    score: CaseScore | AgentScore,
) -> CitationValidationResult:
    if isinstance(score, AgentScore):
        return CitationValidationResult(
            failures=tuple(_collect_agent_failures(score)),
        )
    if isinstance(score, CaseScore):
        return CitationValidationResult(
            failures=tuple(
                _collect_case_failures(score, prefix="")
            ),
        )
    raise TypeError(
        f"validate_citations expects CaseScore or "
        f"AgentScore, got "
        f"{type(score).__name__}"
    )


def _collect_agent_failures(
    score: AgentScore,
) -> list[CitationValidationFailure]:
    failures: list[CitationValidationFailure] = []
    failures.extend(
        _check_dir(score.runs_root, "runs_root")
    )
    failures.extend(
        _check_file(score.manifest_path, "manifest_path")
    )
    for index, case_score in enumerate(score.case_scores):
        failures.extend(
            _collect_case_failures(
                case_score,
                prefix=f"case_scores[{index}]",
            )
        )
    return failures


def _collect_case_failures(
    score: CaseScore,
    *,
    prefix: str,
) -> list[CitationValidationFailure]:
    failures: list[CitationValidationFailure] = []
    qualifier = f"{prefix}." if prefix else ""
    failures.extend(
        _check_dir(
            score.case_dir,
            f"{qualifier}case_dir",
        )
    )
    for index, outcome in enumerate(score.outcomes):
        if isinstance(
            outcome,
            (AssertionPassed, AssertionFailed),
        ):
            failures.extend(
                _check_file(
                    outcome.evidence.artifact_path,
                    f"{qualifier}outcomes[{index}]"
                    f".evidence.artifact_path",
                )
            )
    return failures


def _check_file(
    path: Path,
    score_path: str,
) -> list[CitationValidationFailure]:
    if path.is_file():
        return []
    return [
        CitationValidationFailure(
            score_path=score_path,
            artifact_path=path,
            expected_kind="file",
        )
    ]


def _check_dir(
    path: Path,
    score_path: str,
) -> list[CitationValidationFailure]:
    if path.is_dir():
        return []
    return [
        CitationValidationFailure(
            score_path=score_path,
            artifact_path=path,
            expected_kind="directory",
        )
    ]


__all__ = [
    "CitationValidationFailure",
    "CitationValidationResult",
    "CitedArtifactKind",
    "validate_citations",
]
