"""
Discriminated reasons an assertion outcome is inconclusive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DOMSnapshotUnavailable(_Strict):
    kind: Literal["dom_snapshot_unavailable"] = (
        "dom_snapshot_unavailable"
    )
    expected_artifact_dir: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the directory under "
                "which the post-submit DOM snapshot would "
                "have been written. The driver did not "
                "reach the post-submit capture step in "
                "this run; the assertion cannot be "
                "evaluated without that snapshot."
            ),
        ),
    ]
    recovery: Annotated[
        str,
        Field(
            default=(
                "To proceed: re-run the case with "
                "--submit and confirm the driver reaches "
                "the after-submit capture step. If the "
                "driver raises before that step (typically "
                "MissingAuthEnvVar or "
                "InputElementNotFound), address the "
                "underlying error and re-score."
            ),
            min_length=1,
            description=(
                "Numbered next steps the caller follows "
                "to make the assertion evaluable on a "
                "subsequent run."
            ),
        ),
    ]


class ObservabilitySourceMissing(_Strict):
    kind: Literal["observability_source_missing"] = (
        "observability_source_missing"
    )
    needed_evidence: Annotated[
        Literal[
            "tool_call_log",
            "routing_decision_log",
            "step_count",
        ],
        Field(
            description=(
                "Class of structured evidence the "
                "assertion requires. The Playwright "
                "baseline (network HAR, page event "
                "streams, screenshots, DOM snapshots) "
                "does not carry this information; the "
                "manifest must declare an observability "
                "source that exposes it."
            ),
        ),
    ]
    recovery: Annotated[
        str,
        Field(
            default=(
                "To proceed: declare an observability "
                "source under manifest.observability "
                "(langfuse for tool_call_log and "
                "routing_decision_log; otel for "
                "step_count) and confirm the agent under "
                "evaluation emits the corresponding "
                "spans. Re-run the case with --submit "
                "and re-score."
            ),
            min_length=1,
            description=(
                "Numbered next steps the caller follows "
                "to wire the missing evidence so the "
                "assertion becomes evaluable."
            ),
        ),
    ]


InconclusiveReason = Annotated[
    DOMSnapshotUnavailable | ObservabilitySourceMissing,
    Field(discriminator="kind"),
]


__all__ = [
    "DOMSnapshotUnavailable",
    "InconclusiveReason",
    "ObservabilitySourceMissing",
]
