"""
Evaluate the must_route_to assertion against captured observability evidence.
"""

from __future__ import annotations

from .inconclusive_reasons import (
    ObservabilitySourceMissing,
)
from .outcomes import (
    AssertionInconclusive,
    AssertionOutcome,
)


def evaluate_must_route_to(
    target_agent: str,
) -> AssertionOutcome:
    return AssertionInconclusive(
        assertion_kind="must_route_to",
        target=target_agent,
        reason=ObservabilitySourceMissing(
            needed_evidence="routing_decision_log",
        ),
    )


__all__ = ["evaluate_must_route_to"]
