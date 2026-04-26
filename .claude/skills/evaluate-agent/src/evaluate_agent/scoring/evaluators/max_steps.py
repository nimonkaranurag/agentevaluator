"""
Evaluate the max_steps assertion against the captured step-count record.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.observability.errors import (
    ObservabilityLogMalformedError,
)
from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)
from evaluate_agent.scoring.resolvers.step_count import (
    resolve_step_count,
    step_count_path,
)


def evaluate_max_steps(
    step_limit: int,
    case_dir: Path,
) -> AssertionOutcome:
    try:
        record = resolve_step_count(case_dir)
    except ObservabilityLogMalformedError as exc:
        return AssertionInconclusive(
            assertion_kind="max_steps",
            reason=ObservabilityLogMalformed.from_error(
                exc
            ),
        )
    if record is None:
        return AssertionInconclusive(
            assertion_kind="max_steps",
            reason=ObservabilitySourceMissing(
                needed_evidence="step_count",
                expected_artifact_path=(
                    step_count_path(case_dir)
                ),
            ),
        )
    observed_steps = record.record.total_steps
    if observed_steps <= step_limit:
        return AssertionPassed(
            assertion_kind="max_steps",
            evidence=AssertionEvidence(
                artifact_path=record.path,
                detail=(
                    f"observed {observed_steps} step(s) "
                    f"within limit of {step_limit}"
                ),
            ),
        )
    return AssertionFailed(
        assertion_kind="max_steps",
        expected=f"<= {step_limit}",
        observed=str(observed_steps),
        evidence=AssertionEvidence(
            artifact_path=record.path,
            detail=(
                f"observed {observed_steps} step(s) "
                f"exceeding limit of {step_limit}"
            ),
        ),
    )


__all__ = ["evaluate_max_steps"]
