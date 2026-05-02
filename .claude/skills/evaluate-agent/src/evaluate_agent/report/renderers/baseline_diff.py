"""
Render a BaselineDiff as a Markdown section embedded in the agent report.
"""

from __future__ import annotations

from evaluate_agent.scoring.scores.baseline_diff import (
    AssertionDiff,
    BaselineDiff,
)


def render_baseline_diff_section(
    diff: BaselineDiff,
) -> str:
    sections = [
        _render_header(diff),
        _render_summary(diff),
    ]
    sections.extend(
        _render_bucket(label, bucket)
        for label, bucket in (
            ("Newly failing", diff.newly_failing),
            (
                "Newly inconclusive",
                diff.newly_inconclusive,
            ),
            ("Newly passing", diff.newly_passing),
            ("Introduced", diff.introduced),
            ("Removed", diff.removed),
        )
    )
    return "\n".join(s for s in sections if s)


def _render_header(diff: BaselineDiff) -> str:
    return "\n".join(
        [
            "## Diff vs baseline",
            "",
            f"**Baseline run id:** `{diff.baseline_run_id}`",
            f"**Current run id:** `{diff.current_run_id}`",
            "",
        ]
    )


def _render_summary(diff: BaselineDiff) -> str:
    return "\n".join(
        [
            "| Transition | Count |",
            "| --- | ---: |",
            f"| Newly failing | "
            f"{diff.summary.newly_failing} |",
            f"| Newly inconclusive | "
            f"{diff.summary.newly_inconclusive} |",
            f"| Newly passing | "
            f"{diff.summary.newly_passing} |",
            f"| Introduced | "
            f"{diff.summary.introduced} |",
            f"| Removed | {diff.summary.removed} |",
            f"| Unchanged | {diff.summary.unchanged} |",
            "",
        ]
    )


def _render_bucket(
    label: str,
    bucket: tuple[AssertionDiff, ...],
) -> str:
    if not bucket:
        return ""
    lines = [
        f"### {label}",
        "",
        "| Case | Kind | Target | Baseline | Current |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in bucket:
        lines.append(
            f"| `{entry.case_id}` | "
            f"`{entry.assertion_kind}` | "
            f"{_format_target(entry.target)} | "
            f"{_format_outcome(entry.baseline_outcome)} | "
            f"{_format_outcome(entry.current_outcome)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _format_target(target: str | None) -> str:
    return f"`{target}`" if target is not None else "—"


def _format_outcome(outcome: str | None) -> str:
    return outcome if outcome is not None else "—"


__all__ = ["render_baseline_diff_section"]
