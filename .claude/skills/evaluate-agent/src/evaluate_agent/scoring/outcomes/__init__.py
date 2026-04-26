"""
Outcome data shapes — passed/failed/inconclusive plus the citation evidence.
"""

from .assertion_outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionKind,
    AssertionOutcome,
    AssertionPassed,
)
from .inconclusive_reasons import (
    DOMSnapshotUnavailable,
    InconclusiveReason,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)

__all__ = [
    "AssertionEvidence",
    "AssertionFailed",
    "AssertionInconclusive",
    "AssertionKind",
    "AssertionOutcome",
    "AssertionPassed",
    "DOMSnapshotUnavailable",
    "InconclusiveReason",
    "ObservabilityLogMalformed",
    "ObservabilitySourceMissing",
]
