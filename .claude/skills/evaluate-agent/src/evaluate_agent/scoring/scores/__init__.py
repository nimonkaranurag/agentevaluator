"""
Compose per-assertion outcomes into case-level and agent-level score records.
"""

from .agent_score import AgentScore, score_agent
from .baseline_diff import (
    AssertionDiff,
    AssertionTransition,
    BaselineDiff,
    BaselineDiffSummary,
    OutcomeStatus,
    compute_baseline_diff,
)
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
    "AssertionDiff",
    "AssertionKindRollup",
    "AssertionTargetRollup",
    "AssertionTransition",
    "BaselineDiff",
    "BaselineDiffSummary",
    "CaseOutcomeRollup",
    "CaseScore",
    "OutcomeStatus",
    "TargetedAssertionKind",
    "compute_baseline_diff",
    "score_agent",
    "score_case",
]
