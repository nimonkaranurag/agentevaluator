"""
Outcome data shapes — passed/failed/inconclusive plus the citation evidence.
"""

from .inconclusive_reasons import (
    DOMSnapshotUnavailable,
    InconclusiveReason,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)
from .outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionKind,
    AssertionOutcome,
    AssertionPassed,
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
