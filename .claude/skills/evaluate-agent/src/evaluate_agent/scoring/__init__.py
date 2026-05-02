"""
Score captured cases against their declared assertions.
"""

from .outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
)
from .scores import (
    AgentScore,
    AssertionDiff,
    BaselineDiff,
    BaselineDiffSummary,
    CaseScore,
    compute_baseline_diff,
    score_agent,
    score_case,
)

__all__ = [
    "AgentScore",
    "AssertionDiff",
    "AssertionFailed",
    "AssertionInconclusive",
    "AssertionOutcome",
    "AssertionPassed",
    "BaselineDiff",
    "BaselineDiffSummary",
    "CaseScore",
    "compute_baseline_diff",
    "score_agent",
    "score_case",
]
