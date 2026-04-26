"""
Render a CaseScore as a citation-grounded Markdown narrative.
"""

from __future__ import annotations

from evaluate_agent.common.errors.report import (
    UnresolvedCitationError,
)
from evaluate_agent.scoring import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    CaseScore,
)
from evaluate_agent.scoring.outcomes import (
    DOMSnapshotUnavailable,
    ObservabilitySourceMissing,
)

from .citation_validator import validate_citations


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
    if isinstance(reason, ObservabilitySourceMissing):
        lines.append(
            f"  - Needed evidence: "
            f"`{reason.needed_evidence}`"
        )
    elif isinstance(reason, DOMSnapshotUnavailable):
        lines.append(
            f"  - Expected artifact dir: "
            f"`{reason.expected_artifact_dir}`"
        )
    lines.append(f"  - Recovery: {reason.recovery}")
    lines.append("")
    return lines


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
