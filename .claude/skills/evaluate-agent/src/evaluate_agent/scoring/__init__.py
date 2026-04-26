"""
Score captured cases against their declared assertions.

The public surface is intentionally narrow: composers (score_case,
score_agent) and the two top-level records (CaseScore, AgentScore)
plus the discriminated assertion-outcome variants. Internal types
(rollups, evaluator predicates, resolvers, observability schemas,
inconclusive reasons) are addressable by their full sub-package
path; consumers should reach for them there.
"""

from .outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
)
from .scores import (
    AgentScore,
    CaseScore,
    score_agent,
    score_case,
)

__all__ = [
    "AgentScore",
    "AssertionFailed",
    "AssertionInconclusive",
    "AssertionOutcome",
    "AssertionPassed",
    "CaseScore",
    "score_agent",
    "score_case",
]
