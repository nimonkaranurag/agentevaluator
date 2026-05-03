"""
Failure-mode tests for evaluate_final_response_contains and the post-submit DOM resolution it owns.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.evaluators import (
    evaluate_final_response_contains,
)
from evaluate_agent.scoring.outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    DOMSnapshotTooLarge,
    DOMSnapshotUnavailable,
)


def _write_post_submit_dom(
    case_dir: Path, html: str
) -> Path:
    dom_dir = case_dir / "trace" / "dom"
    dom_dir.mkdir(parents=True)
    path = dom_dir / "step-002-after_submit.html"
    path.write_text(html, encoding="utf-8")
    return path


def test_inconclusive_when_post_submit_dom_missing(
    case_dir: Path,
) -> None:
    # Distinct from "substring not present" — the driver never
    # reached the after-submit capture step. The recovery path
    # is to investigate the driver, not the agent's reply.
    outcome = evaluate_final_response_contains(
        "world", case_dir, max_dom_bytes=1024 * 1024
    )
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, DOMSnapshotUnavailable
    )


def test_passes_with_match_offset_in_evidence_detail(
    case_dir: Path,
) -> None:
    # The detail must surface the matched offset and a
    # surrounding excerpt so the operator can see the matched
    # substring in context — citations without an excerpt force
    # the reader to open the full DOM file.
    _write_post_submit_dom(
        case_dir,
        (
            "<html><body>"
            "<p>Greeting: Hello, world!</p>"
            "</body></html>"
        ),
    )
    outcome = evaluate_final_response_contains(
        "world", case_dir, max_dom_bytes=1024 * 1024
    )
    assert isinstance(outcome, AssertionPassed)
    assert "character offset" in outcome.evidence.detail
    assert "world" in outcome.evidence.detail


def test_fails_with_observed_excerpt_truncated(
    case_dir: Path,
) -> None:
    # Failure path emits the visible text as observed evidence
    # so the operator sees what the agent actually said.
    # Truncation cap (~500 chars) guards against pathological
    # long pages flooding the report.
    body = "x" * 600 + " here"
    _write_post_submit_dom(
        case_dir,
        f"<html><body><p>{body}</p></body></html>",
    )
    outcome = evaluate_final_response_contains(
        "missing-substring",
        case_dir,
        max_dom_bytes=1024 * 1024,
    )
    assert isinstance(outcome, AssertionFailed)
    assert outcome.observed is not None
    assert "[...truncated]" in outcome.observed


def test_fails_when_substring_absent_in_visible_text(
    case_dir: Path,
) -> None:
    _write_post_submit_dom(
        case_dir,
        "<html><body><p>nothing useful</p></body></html>",
    )
    outcome = evaluate_final_response_contains(
        "expected", case_dir, max_dom_bytes=1024 * 1024
    )
    assert isinstance(outcome, AssertionFailed)
    assert outcome.expected == "expected"


def test_inconclusive_when_dom_exceeds_byte_cap(
    case_dir: Path,
) -> None:
    # The cap enforces "fail fast on metadata, do not load
    # multi-hundred-MiB DOMs". The evaluator must surface this
    # as DOMSnapshotTooLarge with the cap and observed size,
    # NOT silently swallow it as a failed assertion.
    _write_post_submit_dom(
        case_dir,
        "<html><body>" + "x" * 5000 + "</body></html>",
    )
    outcome = evaluate_final_response_contains(
        "x", case_dir, max_dom_bytes=1024
    )
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(outcome.reason, DOMSnapshotTooLarge)
    assert outcome.reason.cap_bytes == 1024
    assert outcome.reason.size_bytes > 1024


def test_substring_match_ignores_script_and_style_text(
    case_dir: Path,
) -> None:
    # The evaluator extracts visible text only; a substring
    # that lives in a <script> body is NOT a match, even though
    # it is in the file. This protects against false-passes
    # when the page accidentally inlines the expected token.
    _write_post_submit_dom(
        case_dir,
        (
            "<html><head>"
            "<script>const x = 'expected-token';</script>"
            "</head><body>"
            "<p>visible content</p>"
            "</body></html>"
        ),
    )
    outcome = evaluate_final_response_contains(
        "expected-token",
        case_dir,
        max_dom_bytes=1024 * 1024,
    )
    assert isinstance(outcome, AssertionFailed)
