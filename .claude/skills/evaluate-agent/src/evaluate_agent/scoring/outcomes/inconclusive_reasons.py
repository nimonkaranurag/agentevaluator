"""
Discriminated reasons an assertion outcome is inconclusive.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Annotated, Literal

from evaluate_agent.common.types import StrictFrozen
from pydantic import Field

_SCHEMA_MODULE_PATH = Path(
    importlib.util.find_spec(
        "evaluate_agent.scoring.observability.schema"
    ).origin
).relative_to(
    Path(
        importlib.util.find_spec(
            "evaluate_agent"
        ).submodule_search_locations[0]
    ).parents[1]
)


class DOMSnapshotUnavailable(StrictFrozen):
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


class ObservabilitySourceMissing(StrictFrozen):
    kind: Literal["observability_source_missing"] = (
        "observability_source_missing"
    )
    needed_evidence: Annotated[
        Literal[
            "tool_call_log",
            "routing_decision_log",
            "step_count",
            "generation_log",
        ],
        Field(
            description=(
                "Class of structured evidence the "
                "assertion requires. The Playwright "
                "baseline (network HAR, page event "
                "streams, screenshots, DOM snapshots) "
                "does not carry this information. The "
                "first three kinds (tool_call_log, "
                "routing_decision_log, step_count) can "
                "be populated by either a trace backend "
                "(langfuse, otel) or ui_introspection "
                "when the chat UI itself surfaces the "
                "signal. The fourth kind "
                "(generation_log — token usage, cost, "
                "and latency per LLM generation) is "
                "trace-backend-only: chat UIs do not "
                "expose token counts or costs, so "
                "ui_introspection cannot supply this."
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
                "To proceed, pick the path the missing "
                "evidence supports:\n"
                "  (1) For tool_call_log / "
                "routing_decision_log / step_count — "
                "declare a trace backend under "
                "manifest.observability (langfuse for "
                "all three; otel forward-compat) AND/OR "
                "declare manifest.observability."
                "ui_introspection if the agent's chat "
                "UI surfaces the signal (reasoning "
                "panel, debug drawer, inline tool-call "
                "cards). For ui_introspection, provide "
                "reveal_actions if the panel is "
                "collapsed by default, a description "
                "naming where the entries appear in the "
                "DOM, and exposes listing the evidence "
                "kinds the UI shows.\n"
                "  (2) For generation_log (token "
                "usage / cost / latency) — only the "
                "trace backend path applies. Declare "
                "manifest.observability.langfuse and "
                "confirm the runtime auto-emits "
                "GENERATION observations with usage and "
                "cost_details (Orchestrate's built-in "
                "LangFuse does this when started with "
                "--with-langfuse). UI introspection "
                "cannot supply this — chat UIs do not "
                "render token counts or costs.\n"
                "Either path lands the structured log "
                "at the expected_artifact_path. Re-run "
                "the case with --submit and re-score."
            ),
            min_length=1,
            description=(
                "Numbered next steps the caller follows "
                "to wire the missing evidence so the "
                "assertion becomes evaluable."
            ),
        ),
    ]


class ObservabilityLogMalformed(StrictFrozen):
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
                f"To proceed: open the log file at "
                f"log_path, locate the offending entry "
                f"(line_number when set, otherwise the "
                f"whole document), and correct it to "
                f"validate against the on-disk schema "
                f"in {_SCHEMA_MODULE_PATH}. Required "
                f"fields: tool_name + span_id "
                f"(tool_calls.jsonl); target_agent + "
                f"span_id (routing_decisions.jsonl); "
                f"total_steps + step_span_ids of "
                f"matching length (step_count.json). "
                f"Re-score the case once the file "
                f"validates."
            ),
            min_length=1,
            description=(
                "Numbered next steps the caller follows "
                "to repair the malformed log so the "
                "assertion becomes evaluable."
            ),
        ),
    ]


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
