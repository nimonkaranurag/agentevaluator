"""
Score captured cases against their declared assertions.
"""

from .agent_score import (
    ASSERTION_KIND_SCHEMA_ORDER,
    AgentRollup,
    AgentScore,
    AssertionKindRollup,
    AssertionTargetRollup,
    CaseOutcomeRollup,
    TargetedAssertionKind,
    score_agent,
)
from .case_score import CaseScore, score_case
from .dom_snapshot_resolver import (
    post_submit_dom_snapshot_dir,
    resolve_post_submit_dom_snapshot,
)
from .dom_text import extract_visible_text
from .final_response_contains import (
    evaluate_final_response_contains,
)
from .inconclusive_reasons import (
    DOMSnapshotUnavailable,
    InconclusiveReason,
    ObservabilitySourceMissing,
)
from .max_steps import evaluate_max_steps
from .must_call import evaluate_must_call
from .must_not_call import evaluate_must_not_call
from .must_route_to import evaluate_must_route_to
from .outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionKind,
    AssertionOutcome,
    AssertionPassed,
)

__all__ = [
    "ASSERTION_KIND_SCHEMA_ORDER",
    "AgentRollup",
    "AgentScore",
    "AssertionEvidence",
    "AssertionFailed",
    "AssertionInconclusive",
    "AssertionKind",
    "AssertionKindRollup",
    "AssertionOutcome",
    "AssertionPassed",
    "AssertionTargetRollup",
    "CaseOutcomeRollup",
    "CaseScore",
    "DOMSnapshotUnavailable",
    "InconclusiveReason",
    "ObservabilitySourceMissing",
    "TargetedAssertionKind",
    "evaluate_final_response_contains",
    "evaluate_max_steps",
    "evaluate_must_call",
    "evaluate_must_not_call",
    "evaluate_must_route_to",
    "extract_visible_text",
    "post_submit_dom_snapshot_dir",
    "resolve_post_submit_dom_snapshot",
    "score_agent",
    "score_case",
]
