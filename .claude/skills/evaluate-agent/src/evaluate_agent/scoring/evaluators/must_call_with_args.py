"""
Evaluate must_call_with_args: a tool was called with the declared argument shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from evaluate_agent.manifest.schema import CallSpec
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


def evaluate_must_call_with_args(
    spec: CallSpec,
    case_dir: Path,
) -> AssertionOutcome:
    log = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="must_call_with_args",
        target=spec.tool_name,
        needed_evidence="tool_call_log",
        resolve=resolve_tool_call_log,
        log_path=tool_call_log_path,
    )
    if isinstance(log, AssertionInconclusive):
        return log
    matching_lines: list[int] = []
    for line_number, entry in enumerate(
        log.entries, start=1
    ):
        if entry.tool_name != spec.tool_name:
            continue
        if entry.arguments is None:
            # A tool call captured without arguments cannot
            # satisfy an args-shape assertion. Treat as a
            # non-match — the failure path's evidence already
            # surfaces the captured-vs-expected distinction.
            continue
        if _is_args_subset(spec.args, entry.arguments):
            matching_lines.append(line_number)
    observed_count = len(matching_lines)
    args_summary = _render_args_summary(spec.args)
    if observed_count >= spec.min_count:
        match_summary = (
            ", ".join(str(n) for n in matching_lines)
            if matching_lines
            else "no matches"
        )
        return AssertionPassed(
            assertion_kind="must_call_with_args",
            target=spec.tool_name,
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    f"matched {observed_count} call(s) "
                    f"to {spec.tool_name!r} with args "
                    f"{args_summary} "
                    f"(min_count={spec.min_count}); "
                    f"line(s): {match_summary}"
                ),
            ),
        )
    return AssertionFailed(
        assertion_kind="must_call_with_args",
        target=spec.tool_name,
        expected=(
            f">= {spec.min_count} call(s) to "
            f"{spec.tool_name} with args {args_summary}"
        ),
        observed=f"{observed_count} matching call(s)",
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"observed {observed_count} matching "
                f"call(s) across {len(log.entries)} "
                f"logged tool call(s); required at least "
                f"{spec.min_count}"
            ),
        ),
    )


def _is_args_subset(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> bool:
    # Deep subset: every (key, value) declared in expected
    # must appear in actual with an equal value, recursing into
    # nested mappings. Lists / scalars compare by ==. Extra
    # keys on the actual side are allowed — agents commonly add
    # bookkeeping fields the assertion doesn't care about, and
    # forcing exact equality would brittle every spec.
    for key, expected_value in expected.items():
        if key not in actual:
            return False
        actual_value = actual[key]
        if isinstance(
            expected_value, Mapping
        ) and isinstance(actual_value, Mapping):
            if not _is_args_subset(
                expected_value, actual_value
            ):
                return False
        elif expected_value != actual_value:
            return False
    return True


def _render_args_summary(args: Mapping[str, Any]) -> str:
    if not args:
        return "{}"
    return "{" + ", ".join(sorted(args.keys())) + "}"


__all__ = ["evaluate_must_call_with_args"]
