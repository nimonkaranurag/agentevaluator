"""
Evaluate the max_steps assertion against the captured step-count record.
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
from evaluate_agent.scoring.resolvers.other_resolvers.step_count import (  # noqa: E501
    resolve_step_count,
    step_count_path,
)

from .utils import resolve_observability_log


def evaluate_max_steps(
    step_limit: int,
    case_dir: Path,
) -> AssertionOutcome:
    record = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="max_steps",
        target=None,
        needed_evidence="step_count",
        resolve=resolve_step_count,
        log_path=step_count_path,
    )
    if isinstance(record, AssertionInconclusive):
        return record
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
