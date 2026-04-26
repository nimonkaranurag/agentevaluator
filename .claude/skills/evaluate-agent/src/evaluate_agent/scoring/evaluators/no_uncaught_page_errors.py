"""
Evaluate the no_uncaught_page_errors assertion against the captured page-errors log.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    BaselineTraceArtifactMissing,
    BaselineTraceLogMalformed,
)
from evaluate_agent.scoring.resolvers.baseline_trace.page_errors_log import (  # noqa: E501
    page_errors_log_path,
    resolve_page_errors_log,
)
from evaluate_agent.scoring.structured_log_parsing import (
    StructuredLogParseError,
)

_OBSERVED_TRUNCATION_MAX_CHARS = 200


def evaluate_no_uncaught_page_errors(
    case_dir: Path,
) -> AssertionOutcome:
    try:
        log = resolve_page_errors_log(case_dir)
    except StructuredLogParseError as exc:
        return AssertionInconclusive(
            assertion_kind="no_uncaught_page_errors",
            reason=BaselineTraceLogMalformed.from_error(
                exc
            ),
        )
    if log is None:
        return AssertionInconclusive(
            assertion_kind="no_uncaught_page_errors",
            reason=BaselineTraceArtifactMissing(
                needed_artifact="page_errors_log",
                expected_artifact_path=(
                    page_errors_log_path(case_dir)
                ),
            ),
        )
    if not log.entries:
        return AssertionPassed(
            assertion_kind="no_uncaught_page_errors",
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    "no uncaught page errors recorded "
                    "in baseline trace log"
                ),
            ),
        )
    first = log.entries[0]
    return AssertionFailed(
        assertion_kind="no_uncaught_page_errors",
        expected="zero uncaught page errors",
        observed=_truncated(first.message),
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"first uncaught page error at line 1 "
                f"(ts={first.ts}); "
                f"{len(log.entries)} total uncaught "
                f"error(s) recorded"
            ),
        ),
    )


def _truncated(value: str) -> str:
    if len(value) <= _OBSERVED_TRUNCATION_MAX_CHARS:
        return value
    head = value[:_OBSERVED_TRUNCATION_MAX_CHARS]
    return f"{head}[...truncated]"


__all__ = ["evaluate_no_uncaught_page_errors"]
