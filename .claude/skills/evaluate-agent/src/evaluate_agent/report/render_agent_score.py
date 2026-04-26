"""
Render an AgentScore as a citation-grounded Markdown narrative.
"""

from __future__ import annotations

from evaluate_agent.common.errors.report import (
    UnresolvedCitationError,
)
from evaluate_agent.scoring import AgentScore
from evaluate_agent.scoring.scores.rollups import (
    AgentRollup,
    CaseOutcomeRollup,
)

from .citation_validator import validate_citations
from .render_case_score import compose_case_section


def render_agent_score_markdown(
    score: AgentScore,
) -> str:
    result = validate_citations(score)
    if not result.is_valid:
        raise UnresolvedCitationError(result.failures)
    sections = [
        _render_header(score),
        _render_assertion_summary(score.rollup),
        _render_by_assertion_kind(score.rollup),
        _render_by_target(score.rollup),
        _render_by_case(score.rollup.cases),
        _render_per_case_detail(score),
    ]
    return (
        "\n".join(s for s in sections if s).rstrip() + "\n"
    )


def _render_header(score: AgentScore) -> str:
    return "\n".join(
        [
            f"# Agent evaluation report — "
            f"`{score.agent_name}`",
            "",
            f"**Run id:** `{score.run_id}`",
            f"**Manifest:** `{score.manifest_path}`",
            f"**Runs root:** `{score.runs_root}`",
            "",
        ]
    )


def _render_assertion_summary(
    rollup: AgentRollup,
) -> str:
    return "\n".join(
        [
            "## Summary",
            "",
            "| Metric | Total | Passed | Failed | "
            "Inconclusive |",
            "| --- | ---: | ---: | ---: | ---: |",
            f"| Assertions | "
            f"{rollup.total_assertions} | "
            f"{rollup.passed} | {rollup.failed} | "
            f"{rollup.inconclusive} |",
            "",
        ]
    )


def _render_by_assertion_kind(
    rollup: AgentRollup,
) -> str:
    if not rollup.by_assertion_kind:
        return ""
    lines = [
        "## By assertion kind",
        "",
        "| Kind | Total | Passed | Failed | "
        "Inconclusive |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rollup.by_assertion_kind:
        lines.append(
            f"| `{row.assertion_kind}` | "
            f"{row.total} | {row.passed} | "
            f"{row.failed} | {row.inconclusive} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_by_target(rollup: AgentRollup) -> str:
    if not rollup.by_target:
        return ""
    lines = [
        "## By target",
        "",
        "| Kind | Target | Total | Passed | Failed "
        "| Inconclusive |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rollup.by_target:
        lines.append(
            f"| `{row.assertion_kind}` | "
            f"`{row.target}` | {row.total} | "
            f"{row.passed} | {row.failed} | "
            f"{row.inconclusive} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_by_case(
    cases: CaseOutcomeRollup,
) -> str:
    return "\n".join(
        [
            "## By case",
            "",
            "| Total | Fully passed | With any "
            "failure | With any inconclusive | "
            "With no assertions |",
            "| ---: | ---: | ---: | ---: | ---: |",
            f"| {cases.total} | "
            f"{cases.fully_passed} | "
            f"{cases.with_any_failure} | "
            f"{cases.with_any_inconclusive} | "
            f"{cases.with_no_assertions} |",
            "",
        ]
    )


def _render_per_case_detail(
    score: AgentScore,
) -> str:
    sections = ["## Per-case detail", ""]
    for case_score in score.case_scores:
        sections.append(
            compose_case_section(
                case_score, heading_level=3
            )
        )
    return "\n".join(sections)


__all__ = ["render_agent_score_markdown"]
