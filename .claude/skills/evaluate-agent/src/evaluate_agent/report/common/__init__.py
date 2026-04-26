"""
Report-domain primitives shared across the report sub-packages.
"""

from .citation_validator import (
    CitationValidationFailure,
    CitationValidationResult,
    CitedArtifactKind,
    validate_citations,
)

__all__ = [
    "CitationValidationFailure",
    "CitationValidationResult",
    "CitedArtifactKind",
    "validate_citations",
]
