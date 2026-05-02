"""
Pydantic schema for citation-grounded case narratives.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.schema import Slug
from pydantic import Field

NarrativeObservationKind = Literal[
    "behavior",
    "tool_use",
    "routing",
    "failure_mode",
    "success_mode",
]


class NarrativeCitation(StrictFrozen):
    artifact_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to a captured artifact "
                "under the case directory the narrative "
                "is bound to (screenshot, DOM snapshot, "
                "trace JSONL, observability log). The "
                "narrative citation validator rejects any "
                "path that does not resolve to a regular "
                "file or that resolves outside the bound "
                "case directory."
            ),
        ),
    ]
    locator: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=200,
            description=(
                "Optional locator inside the artifact: "
                "line number for JSONL logs, character "
                "offset for DOM text, span id for "
                "structured observability records. "
                "Rendered verbatim alongside the artifact "
                "path so a reader can navigate from the "
                "report to the precise evidence."
            ),
        ),
    ]


class NarrativeObservation(StrictFrozen):
    kind: Annotated[
        NarrativeObservationKind,
        Field(
            description=(
                "Category of observation. behavior: "
                "general agent behavior. tool_use: tool "
                "invocation patterns. routing: sub-agent "
                "routing decisions. failure_mode: "
                "explanation of a failed or inconclusive "
                "assertion. success_mode: explanation of "
                "a passed assertion."
            ),
        ),
    ]
    claim: Annotated[
        str,
        Field(
            min_length=1,
            max_length=500,
            description=(
                "One-sentence factual statement about "
                "the agent's behavior in this case. The "
                "statement is grounded in the citations "
                "that follow; interpretation that is not "
                "visible in the cited evidence is "
                "outside the contract."
            ),
        ),
    ]
    citations: Annotated[
        tuple[NarrativeCitation, ...],
        Field(
            min_length=1,
            description=(
                "One or more citations grounding the "
                "claim. The citation validator rejects "
                "narratives whose observations carry "
                "zero citations."
            ),
        ),
    ]


class CaseNarrative(StrictFrozen):
    case_id: Annotated[
        Slug,
        Field(
            description=(
                "Case identifier matching the CaseScore "
                "the narrative explains. The renderer "
                "rejects a narrative whose case_id does "
                "not match the score it is bound to."
            ),
        ),
    ]
    summary: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2000,
            description=(
                "One-paragraph synthesis of why the "
                "case passed, failed, or was "
                "inconclusive. Reads as the lede a "
                "human skims first; the supporting "
                "observations carry the citations that "
                "ground the summary's claims."
            ),
        ),
    ]
    observations: Annotated[
        tuple[NarrativeObservation, ...],
        Field(
            min_length=1,
            description=(
                "Ordered list of grounded observations "
                "supporting the summary. Each "
                "observation carries its own citations; "
                "the summary inherits grounding through "
                "the observations it synthesizes."
            ),
        ),
    ]


__all__ = [
    "CaseNarrative",
    "NarrativeCitation",
    "NarrativeObservation",
    "NarrativeObservationKind",
]
