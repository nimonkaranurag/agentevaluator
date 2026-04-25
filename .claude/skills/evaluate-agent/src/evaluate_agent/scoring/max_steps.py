"""
Evaluate the max_steps assertion against captured observability evidence.
"""

from __future__ import annotations

from .inconclusive_reasons import (
    ObservabilitySourceMissing,
)
from .outcomes import (
    AssertionInconclusive,
    AssertionOutcome,
)


def evaluate_max_steps(
    step_limit: int,
) -> AssertionOutcome:
    return AssertionInconclusive(
        assertion_kind="max_steps",
        reason=ObservabilitySourceMissing(
            needed_evidence="step_count",
        ),
    )


__all__ = ["evaluate_max_steps"]
