"""
Evaluate must_call_in_order: declared tools appear in the trace as a subsequence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

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


def evaluate_must_call_in_order(
    expected_sequence: Sequence[str],
    case_dir: Path,
) -> AssertionOutcome:
    log = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="must_call_in_order",
        target=None,
        needed_evidence="tool_call_log",
        resolve=resolve_tool_call_log,
        log_path=tool_call_log_path,
    )
    if isinstance(log, AssertionInconclusive):
        return log
    expected_summary = " -> ".join(expected_sequence)
    pointer = 0
    matched_lines: list[int] = []
    for line_number, entry in enumerate(
        log.entries, start=1
    ):
        if pointer >= len(expected_sequence):
            break
        if entry.tool_name == expected_sequence[pointer]:
            matched_lines.append(line_number)
            pointer += 1
    if pointer == len(expected_sequence):
        match_summary = (
            ", ".join(str(n) for n in matched_lines)
            if matched_lines
            else "empty sequence"
        )
        return AssertionPassed(
            assertion_kind="must_call_in_order",
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    f"matched subsequence "
                    f"{expected_summary}; line(s): "
                    f"{match_summary}"
                ),
            ),
        )
    observed_summary = (
        " -> ".join(
            entry.tool_name for entry in log.entries
        )
        or "empty"
    )
    missing_step = expected_sequence[pointer]
    return AssertionFailed(
        assertion_kind="must_call_in_order",
        expected=expected_summary,
        observed=observed_summary,
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"matched first {pointer} of "
                f"{len(expected_sequence)} step(s) before "
                f"{missing_step!r} could not be matched "
                f"in any subsequent tool call"
            ),
        ),
    )


__all__ = ["evaluate_must_call_in_order"]
