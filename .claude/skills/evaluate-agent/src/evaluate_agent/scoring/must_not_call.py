"""
Evaluate the must_not_call assertion against captured observability evidence.
"""

from __future__ import annotations

from .inconclusive_reasons import (
    ObservabilitySourceMissing,
)
from .outcomes import (
    AssertionInconclusive,
    AssertionOutcome,
)


def evaluate_must_not_call(
    tool_name: str,
) -> AssertionOutcome:
    return AssertionInconclusive(
        assertion_kind="must_not_call",
        target=tool_name,
        reason=ObservabilitySourceMissing(
            needed_evidence="tool_call_log",
        ),
    )


__all__ = ["evaluate_must_not_call"]
