"""
Discriminated reasons an assertion outcome is inconclusive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from evaluate_agent.scoring.structured_log_parsing import (
    StructuredLogParseError,
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
        error: StructuredLogParseError,
    ) -> "ObservabilityLogMalformed":
        return cls(
            log_path=error.path,
            line_number=error.line_number,
            parse_error=error.parse_error,
        )


class BaselineTraceArtifactMissing(_Strict):
    kind: Literal["baseline_trace_artifact_missing"] = (
        "baseline_trace_artifact_missing"
    )
    needed_artifact: Annotated[
        Literal["page_errors_log"],
        Field(
            description=(
                "Class of always-on baseline-trace "
                "evidence the assertion requires. "
                "Baseline-trace artifacts are written "
                "by the driver's TraceCollector on "
                "every session and do not require "
                "manifest configuration; an absent "
                "artifact means the case was never "
                "driven (no open_agent.py invocation) "
                "or the driver crashed before the "
                "trace baseline was opened."
            ),
        ),
    ]
    expected_artifact_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path under which the baseline "
                "trace log resolves once the case is "
                "driven. Cited verbatim in the recovery "
                "procedure so the caller knows the path "
                "the missing log occupies."
            ),
        ),
    ]
    recovery: Annotated[
        str,
        Field(
            default=(
                "To proceed: re-run the case via "
                "open_agent.py (the trace baseline is "
                "always-on and writes the log "
                "automatically). If the driver did "
                "raise during the run, address the "
                "underlying error first — the log is "
                "opened before the agent under "
                "evaluation is reached, so a baseline "
                "trace artifact missing on disk "
                "indicates the driver did not start "
                "session capture at all. Re-score the "
                "case once the artifact lands at the "
                "expected_artifact_path."
            ),
            min_length=1,
            description=(
                "Numbered next steps the caller follows "
                "to make the assertion evaluable."
            ),
        ),
    ]


class BaselineTraceLogMalformed(_Strict):
    kind: Literal["baseline_trace_log_malformed"] = (
        "baseline_trace_log_malformed"
    )
    log_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the baseline-trace log "
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
                "failure applies to the document as a "
                "whole rather than a specific line."
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
                "verbatim so the caller can correct "
                "the offending entry without re-running "
                "the scoring layer."
            ),
        ),
    ]
    recovery: Annotated[
        str,
        Field(
            default=(
                "To proceed: open the log file at "
                "log_path and correct the offending "
                "entry (line_number when set, "
                "otherwise the whole document) so it "
                "validates against the on-disk schema "
                "in src/evaluate_agent/scoring/"
                "baseline_trace/schema.py. "
                "Baseline-trace logs are written by "
                "the driver's TraceCollector — a "
                "malformed entry typically indicates "
                "the file was edited by hand or "
                "truncated mid-write; re-running the "
                "case via open_agent.py overwrites "
                "the file cleanly. Re-score the case "
                "once the file validates."
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
        error: StructuredLogParseError,
    ) -> "BaselineTraceLogMalformed":
        return cls(
            log_path=error.path,
            line_number=error.line_number,
            parse_error=error.parse_error,
        )


InconclusiveReason = Annotated[
    DOMSnapshotUnavailable
    | ObservabilitySourceMissing
    | ObservabilityLogMalformed
    | BaselineTraceArtifactMissing
    | BaselineTraceLogMalformed,
    Field(discriminator="kind"),
]


__all__ = [
    "BaselineTraceArtifactMissing",
    "BaselineTraceLogMalformed",
    "DOMSnapshotUnavailable",
    "InconclusiveReason",
    "ObservabilityLogMalformed",
    "ObservabilitySourceMissing",
]
