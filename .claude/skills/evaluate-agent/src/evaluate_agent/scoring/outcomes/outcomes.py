"""
Discriminated assertion outcomes with citation-shaped evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from .inconclusive_reasons import InconclusiveReason


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


AssertionKind = Literal[
    "final_response_contains",
    "must_call",
    "must_not_call",
    "must_route_to",
    "max_steps",
]


class AssertionEvidence(_Strict):
    artifact_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the captured artifact "
                "supporting the outcome. Reports cite this "
                "path verbatim so a reader can open the "
                "file and inspect the evidence."
            ),
        ),
    ]
    detail: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Free-form locator within the artifact. "
                "For DOM snapshot citations: the matched "
                "substring's character offset and a short "
                "surrounding excerpt. For trace log "
                "citations: span id and line number."
            ),
        ),
    ]


class AssertionPassed(_Strict):
    outcome: Literal["passed"] = "passed"
    assertion_kind: Annotated[
        AssertionKind,
        Field(
            description=(
                "Schema-level kind of the assertion that "
                "passed. Mirrors the field name on "
                "manifest.cases[].assertions."
            ),
        ),
    ]
    target: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Specific subject of the assertion when "
                "the assertion iterates per-target "
                "(must_call / must_not_call: the tool "
                "name; must_route_to: the agent name). "
                "None for whole-case assertions "
                "(final_response_contains, max_steps)."
            ),
        ),
    ]
    evidence: Annotated[
        AssertionEvidence,
        Field(
            description=(
                "Citation that resolves to a real "
                "captured artifact. Every passed outcome "
                "is grounded in evidence the caller can "
                "inspect."
            ),
        ),
    ]


class AssertionFailed(_Strict):
    outcome: Literal["failed"] = "failed"
    assertion_kind: Annotated[
        AssertionKind,
        Field(
            description=(
                "Schema-level kind of the assertion that "
                "failed. Mirrors the field name on "
                "manifest.cases[].assertions."
            ),
        ),
    ]
    target: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Specific subject of the assertion when "
                "the assertion iterates per-target. None "
                "for whole-case assertions."
            ),
        ),
    ]
    expected: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "What the assertion required, rendered "
                "as a string. For final_response_contains "
                "the expected substring; for must_call "
                "the tool name; for max_steps the "
                "integer limit serialized as text."
            ),
        ),
    ]
    observed: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Value found in the captured artifact, "
                "rendered as a string. None when the "
                "artifact carries no comparable value "
                "(e.g. an empty post-submit DOM)."
            ),
        ),
    ]
    evidence: Annotated[
        AssertionEvidence,
        Field(
            description=(
                "Citation that resolves to a real "
                "captured artifact. Every failed "
                "outcome is grounded in evidence the "
                "caller can inspect to confirm the "
                "discrepancy."
            ),
        ),
    ]


class AssertionInconclusive(_Strict):
    outcome: Literal["inconclusive"] = "inconclusive"
    assertion_kind: Annotated[
        AssertionKind,
        Field(
            description=(
                "Schema-level kind of the assertion that "
                "could not be evaluated. Mirrors the "
                "field name on manifest.cases[]."
                "assertions."
            ),
        ),
    ]
    target: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Specific subject of the assertion when "
                "the assertion iterates per-target. None "
                "for whole-case assertions."
            ),
        ),
    ]
    reason: Annotated[
        InconclusiveReason,
        Field(
            description=(
                "Discriminated reason naming the "
                "evidence the assertion requires but the "
                "captured trace lacks, plus the recovery "
                "procedure the caller follows to make the "
                "assertion evaluable on a subsequent run."
            ),
        ),
    ]


AssertionOutcome = Annotated[
    AssertionPassed
    | AssertionFailed
    | AssertionInconclusive,
    Field(discriminator="outcome"),
]


__all__ = [
    "AssertionEvidence",
    "AssertionFailed",
    "AssertionInconclusive",
    "AssertionKind",
    "AssertionOutcome",
    "AssertionPassed",
]
