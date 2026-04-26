"""
Render a CaseScore as a citation-grounded Markdown narrative.
"""

from __future__ import annotations

from typing import Callable

from ..scoring import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    BaselineTraceArtifactMissing,
    BaselineTraceLogMalformed,
    CaseScore,
    DOMSnapshotUnavailable,
    InconclusiveReason,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)
from .citation_validator import validate_citations
from .errors import UnresolvedCitationError


def render_case_score_markdown(
    score: CaseScore,
) -> str:
    result = validate_citations(score)
    if not result.is_valid:
        raise UnresolvedCitationError(result.failures)
    return compose_case_section(score, heading_level=1)


def compose_case_section(
    score: CaseScore,
    *,
    heading_level: int,
) -> str:
    if not 1 <= heading_level <= 6:
        raise ValueError(
            f"heading_level must be between 1 and 6 "
            f"inclusive (Markdown ATX heading depth); "
            f"got {heading_level}"
        )
    h = "#" * heading_level
    summary = _case_summary_line(score)
    lines = [
        f"{h} Case `{score.case_id}` — {summary}",
        "",
        f"**Directory:** `{score.case_dir}`",
        "",
    ]
    if not score.outcomes:
        lines.append(
            "No assertions declared for this case."
        )
        return "\n".join(lines).rstrip() + "\n"
    lines.append("**Assertion outcomes:**")
    lines.append("")
    for outcome in score.outcomes:
        lines.extend(_render_outcome(outcome))
    return "\n".join(lines).rstrip() + "\n"


def _case_summary_line(score: CaseScore) -> str:
    return (
        f"{score.passed} passed, "
        f"{score.failed} failed, "
        f"{score.inconclusive} inconclusive "
        f"(of {score.total} total)"
    )


def _render_outcome(
    outcome: AssertionOutcome,
) -> list[str]:
    if isinstance(outcome, AssertionPassed):
        return _render_passed(outcome)
    if isinstance(outcome, AssertionFailed):
        return _render_failed(outcome)
    if isinstance(outcome, AssertionInconclusive):
        return _render_inconclusive(outcome)
    raise TypeError(
        f"unknown outcome type: "
        f"{type(outcome).__name__}"
    )


def _render_passed(
    outcome: AssertionPassed,
) -> list[str]:
    lines = [
        f"- {_outcome_header('PASSED', outcome)}",
        f"  - Evidence: "
        f"`{outcome.evidence.artifact_path}`",
    ]
    if outcome.evidence.detail is not None:
        lines.append(
            f"  - Detail: {outcome.evidence.detail}"
        )
    lines.append("")
    return lines


def _render_failed(
    outcome: AssertionFailed,
) -> list[str]:
    lines = [
        f"- {_outcome_header('FAILED', outcome)}",
        f"  - Expected: `{outcome.expected}`",
    ]
    if outcome.observed is None:
        lines.append("  - Observed: (none)")
    else:
        lines.append(f"  - Observed: `{outcome.observed}`")
    lines.append(
        f"  - Evidence: "
        f"`{outcome.evidence.artifact_path}`"
    )
    if outcome.evidence.detail is not None:
        lines.append(
            f"  - Detail: {outcome.evidence.detail}"
        )
    lines.append("")
    return lines


def _render_inconclusive(
    outcome: AssertionInconclusive,
) -> list[str]:
    reason = outcome.reason
    lines = [
        f"- {_outcome_header('INCONCLUSIVE', outcome)}",
        f"  - Reason: `{reason.kind}`",
    ]
    lines.extend(_render_reason_specific_lines(reason))
    lines.append(f"  - Recovery: {reason.recovery}")
    lines.append("")
    return lines


def _render_reason_specific_lines(
    reason: InconclusiveReason,
) -> list[str]:
    renderer = _REASON_RENDERERS.get(type(reason))
    if renderer is None:
        raise TypeError(
            f"no renderer registered for "
            f"InconclusiveReason variant "
            f"{type(reason).__name__}; register it in "
            f"_REASON_RENDERERS so the renderer stays "
            f"exhaustive over the discriminated union."
        )
    return renderer(reason)


def _render_dom_snapshot_unavailable(
    reason: DOMSnapshotUnavailable,
) -> list[str]:
    return [
        f"  - Expected artifact dir: "
        f"`{reason.expected_artifact_dir}`",
    ]


def _render_observability_source_missing(
    reason: ObservabilitySourceMissing,
) -> list[str]:
    return [
        f"  - Needed evidence: "
        f"`{reason.needed_evidence}`",
        f"  - Expected artifact path: "
        f"`{reason.expected_artifact_path}`",
    ]


def _render_observability_log_malformed(
    reason: ObservabilityLogMalformed,
) -> list[str]:
    return _render_log_malformed_lines(
        log_path=reason.log_path,
        line_number=reason.line_number,
        parse_error=reason.parse_error,
    )


def _render_baseline_trace_artifact_missing(
    reason: BaselineTraceArtifactMissing,
) -> list[str]:
    return [
        f"  - Needed artifact: "
        f"`{reason.needed_artifact}`",
        f"  - Expected artifact path: "
        f"`{reason.expected_artifact_path}`",
    ]


def _render_baseline_trace_log_malformed(
    reason: BaselineTraceLogMalformed,
) -> list[str]:
    return _render_log_malformed_lines(
        log_path=reason.log_path,
        line_number=reason.line_number,
        parse_error=reason.parse_error,
    )


def _render_log_malformed_lines(
    *,
    log_path,
    line_number,
    parse_error,
) -> list[str]:
    lines = [f"  - Log path: `{log_path}`"]
    if line_number is not None:
        lines.append(f"  - Line number: {line_number}")
    lines.append(f"  - Parse error: `{parse_error}`")
    return lines


_REASON_RENDERERS: dict[
    type, Callable[[InconclusiveReason], list[str]]
] = {
    DOMSnapshotUnavailable: (
        _render_dom_snapshot_unavailable
    ),
    ObservabilitySourceMissing: (
        _render_observability_source_missing
    ),
    ObservabilityLogMalformed: (
        _render_observability_log_malformed
    ),
    BaselineTraceArtifactMissing: (
        _render_baseline_trace_artifact_missing
    ),
    BaselineTraceLogMalformed: (
        _render_baseline_trace_log_malformed
    ),
}


def _outcome_header(
    status: str,
    outcome: AssertionOutcome,
) -> str:
    base = f"**{status}** `{outcome.assertion_kind}`"
    if outcome.target is None:
        return base
    return f"{base} — target `{outcome.target}`"


__all__ = [
    "compose_case_section",
    "render_case_score_markdown",
]
