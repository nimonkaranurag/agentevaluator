"""
Outcome data shapes — passed/failed/inconclusive plus the citation evidence.
"""

from .inconclusive_reasons import (
    BaselineTraceArtifactMissing,
    BaselineTraceLogMalformed,
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
    "BaselineTraceArtifactMissing",
    "BaselineTraceLogMalformed",
    "DOMSnapshotUnavailable",
    "InconclusiveReason",
    "ObservabilityLogMalformed",
    "ObservabilitySourceMissing",
]
