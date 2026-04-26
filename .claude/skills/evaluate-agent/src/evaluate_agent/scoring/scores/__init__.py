"""
Compose per-assertion outcomes into case-level and agent-level score records.
"""

from .agent_score import AgentScore, score_agent
from .case_score import CaseScore, score_case
from .rollups import (
    ASSERTION_KIND_SCHEMA_ORDER,
    AgentRollup,
    AssertionKindRollup,
    AssertionTargetRollup,
    CaseOutcomeRollup,
    TargetedAssertionKind,
)

__all__ = [
    "ASSERTION_KIND_SCHEMA_ORDER",
    "AgentRollup",
    "AgentScore",
    "AssertionKindRollup",
    "AssertionTargetRollup",
    "CaseOutcomeRollup",
    "CaseScore",
    "TargetedAssertionKind",
    "score_agent",
    "score_case",
]
