"""
Evaluate must_call_exactly: each named tool was called the required number of times.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
)
from evaluate_agent.scoring.resolvers.log_resolvers.tool_call_log import (  # noqa: E501
    resolve_tool_call_log,
    tool_call_log_path,
)

from .utils import resolve_observability_log


def evaluate_must_call_exactly(
    tool_name: str,
    required_count: int,
    case_dir: Path,
) -> AssertionOutcome:
    log = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="must_call_exactly",
        target=tool_name,
        needed_evidence="tool_call_log",
        resolve=resolve_tool_call_log,
        log_path=tool_call_log_path,
    )
    if isinstance(log, AssertionInconclusive):
        return log
    matching_lines = [
        line_number
        for line_number, entry in enumerate(
            log.entries, start=1
        )
        if entry.tool_name == tool_name
    ]
    observed_count = len(matching_lines)
    if observed_count == required_count:
        # Cite every matched line so the renderer can point
        # the reader at each invocation rather than just the
        # first one — must_call_exactly's value is in the
        # count, so the evidence has to surface every match.
        match_summary = (
            ", ".join(str(n) for n in matching_lines)
            if matching_lines
            else "no matches"
        )
        return AssertionPassed(
            assertion_kind="must_call_exactly",
            target=tool_name,
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    f"matched {observed_count} call(s); "
                    f"line(s): {match_summary}"
                ),
            ),
        )
    return AssertionFailed(
        assertion_kind="must_call_exactly",
        target=tool_name,
        expected=f"exactly {required_count} call(s)",
        observed=f"{observed_count} call(s)",
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"observed {observed_count} call(s) to "
                f"{tool_name!r} across "
                f"{len(log.entries)} logged tool call(s); "
                f"required exactly {required_count}"
            ),
        ),
    )


__all__ = ["evaluate_must_call_exactly"]
