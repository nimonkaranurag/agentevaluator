"""
Citation-grounded case narratives that explain why a case passed, failed, or was inconclusive.
"""

from .citation_validator import (
    NarrativeCitationFailure,
    NarrativeCitationFailureReason,
    NarrativeCitationValidationResult,
    validate_narrative_citations,
    verify_narrative_against_score,
)
from .loader import load_case_narrative
from .schema import (
    CaseNarrative,
    NarrativeCitation,
    NarrativeObservation,
    NarrativeObservationKind,
)

__all__ = [
    "CaseNarrative",
    "NarrativeCitation",
    "NarrativeCitationFailure",
    "NarrativeCitationFailureReason",
    "NarrativeCitationValidationResult",
    "NarrativeObservation",
    "NarrativeObservationKind",
    "load_case_narrative",
    "validate_narrative_citations",
    "verify_narrative_against_score",
]
