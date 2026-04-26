"""
Discriminated reasons an assertion outcome is inconclusive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from evaluate_agent.scoring.observability.errors import (
    ObservabilityLogMalformedError,
)
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
    expected_artifact_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path under which the "
                "structured log would resolve once the "
                "observability source is wired. Cited "
                "verbatim in the recovery procedure so "
                "the caller knows where to land the "
                "log."
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
                "spans. Land the structured log at the "
                "expected_artifact_path. Re-run the case "
                "with --submit and re-score."
            ),
            min_length=1,
            description=(
                "Numbered next steps the caller follows "
                "to wire the missing evidence so the "
                "assertion becomes evaluable."
            ),
        ),
    ]


class ObservabilityLogMalformed(_Strict):
    kind: Literal["observability_log_malformed"] = (
        "observability_log_malformed"
    )
    log_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the observability log "
                "file that was present on disk but "
                "could not be parsed. Cited verbatim so "
                "the caller can open the file and "
                "inspect the offending entry."
            ),
        ),
    ]
    line_number: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description=(
                "1-based line number of the offending "
                "entry inside the log. None when the "
                "log is a single JSON document and the "
                "failure applies to the document as a "
                "whole (e.g. step_count.json)."
            ),
        ),
    ]
    parse_error: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Underlying parse-error message — "
                "either a JSON syntax error or a "
                "schema-validation summary. Cited "
                "verbatim so the caller can correct the "
                "offending entry without re-running the "
                "scoring layer."
            ),
        ),
    ]
    recovery: Annotated[
        str,
        Field(
            default=(
                "To proceed: open the log file at "
                "log_path, locate the offending entry "
                "(line_number when set, otherwise the "
                "whole document), and correct it to "
                "validate against the on-disk schema "
                "in src/evaluate_agent/scoring/"
                "observability/schema.py. Required "
                "fields: tool_name + span_id "
                "(tool_calls.jsonl); target_agent + "
                "span_id (routing_decisions.jsonl); "
                "total_steps + step_span_ids of "
                "matching length (step_count.json). "
                "Re-score the case once the file "
                "validates."
            ),
            min_length=1,
            description=(
                "Numbered next steps the caller follows "
                "to repair the malformed log so the "
                "assertion becomes evaluable."
            ),
        ),
    ]

    @classmethod
    def from_error(
        cls,
        error: ObservabilityLogMalformedError,
    ) -> "ObservabilityLogMalformed":
        return cls(
            log_path=error.path,
            line_number=error.line_number,
            parse_error=error.parse_error,
        )


InconclusiveReason = Annotated[
    DOMSnapshotUnavailable
    | ObservabilitySourceMissing
    | ObservabilityLogMalformed,
    Field(discriminator="kind"),
]


__all__ = [
    "DOMSnapshotUnavailable",
    "InconclusiveReason",
    "ObservabilityLogMalformed",
    "ObservabilitySourceMissing",
]
