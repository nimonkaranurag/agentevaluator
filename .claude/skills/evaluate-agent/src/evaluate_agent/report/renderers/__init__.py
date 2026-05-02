"""
Markdown renderers, one per score-record type.
"""

from .agent_score import render_agent_score_markdown
from .baseline_diff import render_baseline_diff_section
from .case_narrative import (
    compose_case_narrative_section,
    render_case_narrative_section,
)
from .case_score import (
    compose_case_section,
    render_case_score_markdown,
)

__all__ = [
    "compose_case_narrative_section",
    "compose_case_section",
    "render_agent_score_markdown",
    "render_baseline_diff_section",
    "render_case_narrative_section",
    "render_case_score_markdown",
]
