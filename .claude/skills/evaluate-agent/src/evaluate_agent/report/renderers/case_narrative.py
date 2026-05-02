"""
Render a CaseNarrative as a citation-grounded Markdown section embedded under a case score.
"""

from __future__ import annotations

from evaluate_agent.case_narrative import (
    CaseNarrative,
    NarrativeCitation,
    NarrativeObservation,
    verify_narrative_against_score,
)
from evaluate_agent.scoring import CaseScore


def render_case_narrative_section(
    narrative: CaseNarrative,
    *,
    score: CaseScore,
    heading_level: int,
) -> str:
    verify_narrative_against_score(narrative, score=score)
    return compose_case_narrative_section(
        narrative, heading_level=heading_level
    )


def compose_case_narrative_section(
    narrative: CaseNarrative,
    *,
    heading_level: int,
) -> str:
    if not 1 <= heading_level <= 6:
        raise ValueError(
            f"heading_level must be between 1 and 6 "
            f"inclusive (Markdown ATX heading depth); "
            f"got {heading_level}"
        )
    h = "#" * heading_level
    sub_h = "#" * min(heading_level + 1, 6)
    lines = [
        f"{h} Analytical narrative",
        "",
        narrative.summary,
        "",
        f"{sub_h} Observations",
        "",
    ]
    for observation in narrative.observations:
        lines.extend(_render_observation(observation))
    return "\n".join(lines).rstrip() + "\n"


def _render_observation(
    observation: NarrativeObservation,
) -> list[str]:
    lines = [
        f"- **{observation.kind}** — "
        f"{observation.claim}",
    ]
    for citation in observation.citations:
        lines.append(_render_citation_line(citation))
    lines.append("")
    return lines


def _render_citation_line(
    citation: NarrativeCitation,
) -> str:
    base = f"  - Evidence: `{citation.artifact_path}`"
    if citation.locator is None:
        return base
    return f"{base} (locator: {citation.locator})"


__all__ = [
    "compose_case_narrative_section",
    "render_case_narrative_section",
]
