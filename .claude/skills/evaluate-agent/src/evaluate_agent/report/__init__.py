"""
Render score records as citation-grounded Markdown narratives.
"""

from evaluate_agent.common.errors.report import (
    UnresolvedCitationError,
)

from .common import (
    CitationValidationFailure,
    CitationValidationResult,
    CitedArtifactKind,
    validate_citations,
)
from .renderers import (
    compose_case_narrative_section,
    compose_case_section,
    render_agent_score_markdown,
    render_baseline_diff_section,
    render_case_narrative_section,
    render_case_score_markdown,
)

__all__ = [
    "CitationValidationFailure",
    "CitationValidationResult",
    "CitedArtifactKind",
    "UnresolvedCitationError",
    "compose_case_narrative_section",
    "compose_case_section",
    "render_agent_score_markdown",
    "render_baseline_diff_section",
    "render_case_narrative_section",
    "render_case_score_markdown",
    "validate_citations",
]
