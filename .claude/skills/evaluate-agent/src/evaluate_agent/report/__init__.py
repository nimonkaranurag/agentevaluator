"""
Render score records as citation-grounded Markdown narratives.
"""

from evaluate_agent.common.errors.report import (
    UnresolvedCitationError,
)

from .citation_validator import (
    CitationValidationFailure,
    CitationValidationResult,
    CitedArtifactKind,
    validate_citations,
)
from .render_agent_score import (
    render_agent_score_markdown,
)
from .render_case_score import (
    compose_case_section,
    render_case_score_markdown,
)

__all__ = [
    "CitationValidationFailure",
    "CitationValidationResult",
    "CitedArtifactKind",
    "UnresolvedCitationError",
    "compose_case_section",
    "render_agent_score_markdown",
    "render_case_score_markdown",
    "validate_citations",
]
