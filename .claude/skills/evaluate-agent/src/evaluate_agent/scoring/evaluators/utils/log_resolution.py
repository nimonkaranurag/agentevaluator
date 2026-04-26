"""
Shared resolution boilerplate the per-assertion evaluators reuse.
"""

from __future__ import annotations

from pathlib import Path
from typing import (
    Callable,
    Literal,
    TypeVar,
)

from evaluate_agent.common.errors.scoring import (
    ObservabilityLogMalformedError,
)
from evaluate_agent.scoring.outcomes import (
    AssertionInconclusive,
    AssertionKind,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)

R = TypeVar("R")

_NeededEvidence = Literal[
    "tool_call_log",
    "routing_decision_log",
    "step_count",
]


def resolve_observability_log(
    *,
    case_dir: Path,
    assertion_kind: AssertionKind,
    target: str | None,
    needed_evidence: _NeededEvidence,
    resolve: Callable[[Path], R | None],
    log_path: Callable[[Path], Path],
) -> R | AssertionInconclusive:
    try:
        log = resolve(case_dir)
    except ObservabilityLogMalformedError as exc:
        return AssertionInconclusive(
            assertion_kind=assertion_kind,
            target=target,
            reason=ObservabilityLogMalformed(
                log_path=exc.path,
                line_number=exc.line_number,
                parse_error=exc.parse_error,
            ),
        )
    if log is None:
        return AssertionInconclusive(
            assertion_kind=assertion_kind,
            target=target,
            reason=ObservabilitySourceMissing(
                needed_evidence=needed_evidence,
                expected_artifact_path=log_path(case_dir),
            ),
        )
    return log


__all__ = ["resolve_observability_log"]
