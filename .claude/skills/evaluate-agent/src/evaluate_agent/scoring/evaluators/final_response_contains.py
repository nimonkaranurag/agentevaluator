"""
Evaluate the final_response_contains assertion against the post-submit DOM.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    DOMSnapshotUnavailable,
)
from evaluate_agent.scoring.resolvers.other_resolvers.dom_snapshot import (  # noqa: E501
    post_submit_dom_snapshot_dir,
    resolve_post_submit_dom_snapshot,
)

_OBSERVED_EXCERPT_MAX_CHARS = 500
_MATCH_EXCERPT_PADDING = 80


def evaluate_final_response_contains(
    expected_substring: str,
    case_dir: Path,
) -> AssertionOutcome:
    snapshot = resolve_post_submit_dom_snapshot(case_dir)
    if snapshot is None:
        return AssertionInconclusive(
            assertion_kind="final_response_contains",
            reason=DOMSnapshotUnavailable(
                expected_artifact_dir=(
                    post_submit_dom_snapshot_dir(case_dir)
                ),
            ),
        )

    visible_text = snapshot.visible_text
    match_offset = visible_text.find(expected_substring)
    if match_offset >= 0:
        return AssertionPassed(
            assertion_kind="final_response_contains",
            evidence=AssertionEvidence(
                artifact_path=snapshot.path,
                detail=_passed_detail(
                    visible_text=visible_text,
                    expected_substring=expected_substring,
                    match_offset=match_offset,
                ),
            ),
        )

    return AssertionFailed(
        assertion_kind="final_response_contains",
        expected=expected_substring,
        observed=_truncate(visible_text),
        evidence=AssertionEvidence(
            artifact_path=snapshot.path,
            detail=(
                f"expected substring not present in "
                f"extracted visible text "
                f"({len(visible_text)} characters)"
            ),
        ),
    )


def _passed_detail(
    visible_text: str,
    expected_substring: str,
    match_offset: int,
) -> str:
    end = match_offset + len(expected_substring)
    excerpt_start = max(
        0, match_offset - _MATCH_EXCERPT_PADDING
    )
    excerpt_end = min(
        len(visible_text),
        end + _MATCH_EXCERPT_PADDING,
    )
    excerpt = visible_text[excerpt_start:excerpt_end]
    return (
        f"matched substring at character offset "
        f"{match_offset} of extracted visible text; "
        f"surrounding excerpt: {excerpt!r}"
    )


def _truncate(text: str) -> str | None:
    if not text:
        return None
    if len(text) <= _OBSERVED_EXCERPT_MAX_CHARS:
        return text
    return (
        text[:_OBSERVED_EXCERPT_MAX_CHARS]
        + " [...truncated]"
    )


__all__ = ["evaluate_final_response_contains"]
