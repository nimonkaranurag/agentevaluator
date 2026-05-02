"""
Render an AgentScore as a citation-grounded Markdown narrative.
"""

from __future__ import annotations

from collections.abc import Mapping

from evaluate_agent.case_narrative import (
    CaseNarrative,
    verify_narrative_against_score,
)
from evaluate_agent.common.errors.case_narrative import (
    NarrativeUnknownCaseIdsError,
)
from evaluate_agent.common.errors.report import (
    UnresolvedCitationError,
)
from evaluate_agent.report.common.citation_validator import (
    validate_citations,
)
from evaluate_agent.scoring import AgentScore
from evaluate_agent.scoring.scores.baseline_diff import (
    BaselineDiff,
)
from evaluate_agent.scoring.scores.rollups import (
    AgentRollup,
    CaseOutcomeRollup,
)

from .baseline_diff import render_baseline_diff_section
from .case_score import compose_case_section


def render_agent_score_markdown(
    score: AgentScore,
    *,
    narratives: Mapping[str, CaseNarrative] | None = None,
    baseline_diff: BaselineDiff | None = None,
) -> str:
    result = validate_citations(score)
    if not result.is_valid:
        raise UnresolvedCitationError(result.failures)
    bound = _bind_narratives_to_cases(
        score, narratives or {}
    )
    diff = (
        baseline_diff
        if baseline_diff is not None
        else score.baseline_diff
    )
    sections = [
        _render_header(score),
        _render_assertion_summary(score.rollup),
        _render_by_assertion_kind(score.rollup),
        _render_by_target(score.rollup),
        _render_by_case(score.rollup.cases),
        (
            render_baseline_diff_section(diff)
            if diff is not None
            else ""
        ),
        _render_per_case_detail(score, bound),
    ]
    return (
        "\n".join(s for s in sections if s).rstrip() + "\n"
    )


def _bind_narratives_to_cases(
    score: AgentScore,
    narratives: Mapping[str, CaseNarrative],
) -> dict[str, CaseNarrative]:
    case_id_to_score = {
        case.case_id: case for case in score.case_scores
    }
    unknown = tuple(
        sorted(set(narratives) - set(case_id_to_score))
    )
    if unknown:
        raise NarrativeUnknownCaseIdsError(
            unknown_case_ids=unknown,
            declared_case_ids=tuple(
                sorted(case_id_to_score)
            ),
        )
    bound: dict[str, CaseNarrative] = {}
    for case_id, narrative in narratives.items():
        verify_narrative_against_score(
            narrative,
            score=case_id_to_score[case_id],
        )
        bound[case_id] = narrative
    return bound


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
    bound_narratives: dict[str, CaseNarrative],
) -> str:
    sections = ["## Per-case detail", ""]
    for case_score in score.case_scores:
        sections.append(
            compose_case_section(
                case_score,
                heading_level=3,
                narrative=bound_narratives.get(
                    case_score.case_id
                ),
            )
        )
    return "\n".join(sections)


__all__ = ["render_agent_score_markdown"]
