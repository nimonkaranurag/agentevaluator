"""
Evaluate the must_call assertion against the captured tool-call log.
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


def evaluate_must_call(
    tool_name: str,
    case_dir: Path,
) -> AssertionOutcome:
    log = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="must_call",
        target=tool_name,
        needed_evidence="tool_call_log",
        resolve=resolve_tool_call_log,
        log_path=tool_call_log_path,
    )
    if isinstance(log, AssertionInconclusive):
        return log
    for line_number, entry in enumerate(
        log.entries, start=1
    ):
        if entry.tool_name == tool_name:
            return AssertionPassed(
                assertion_kind="must_call",
                target=tool_name,
                evidence=AssertionEvidence(
                    artifact_path=log.path,
                    detail=(
                        f"matched at line {line_number} "
                        f"(span_id={entry.span_id})"
                    ),
                ),
            )
    observed_tool_names = sorted(
        {entry.tool_name for entry in log.entries}
    )
    return AssertionFailed(
        assertion_kind="must_call",
        target=tool_name,
        expected=tool_name,
        observed=", ".join(observed_tool_names) or None,
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"tool not found in {len(log.entries)} "
                f"logged tool call(s)"
            ),
        ),
    )


__all__ = ["evaluate_must_call"]
