"""
Tests for evaluate_final_response_contains against captured DOM snapshots.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.final_response_contains import (
    evaluate_final_response_contains,
)
from evaluate_agent.scoring.inconclusive_reasons import (
    DOMSnapshotUnavailable,
)
from evaluate_agent.scoring.outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
)


def _seed_after_submit_dom(
    case_dir: Path,
    html: str,
    step_number: int = 2,
) -> Path:
    dom_dir = case_dir / "trace" / "dom"
    dom_dir.mkdir(parents=True, exist_ok=True)
    target = (
        dom_dir
        / f"step-{step_number:03d}-after_submit.html"
    )
    target.write_text(html, encoding="utf-8")
    return target


class TestInconclusivePath:
    def test_no_dom_dir_returns_inconclusive(
        self, tmp_path
    ):
        outcome = evaluate_final_response_contains(
            expected_substring="confirmed",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert (
            outcome.assertion_kind
            == "final_response_contains"
        )
        assert isinstance(
            outcome.reason, DOMSnapshotUnavailable
        )
        assert (
            outcome.reason.expected_artifact_dir
            == tmp_path / "trace" / "dom"
        )

    def test_dom_dir_without_after_submit_inconclusive(
        self, tmp_path
    ):
        dom_dir = tmp_path / "trace" / "dom"
        dom_dir.mkdir(parents=True)
        (dom_dir / "step-001-landing.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        outcome = evaluate_final_response_contains(
            expected_substring="confirmed",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, DOMSnapshotUnavailable
        )


class TestPassedPath:
    def test_substring_present_returns_passed(
        self, tmp_path
    ):
        snapshot = _seed_after_submit_dom(
            tmp_path,
            "<html><body>"
            "<p>Booking confirmed for tomorrow</p>"
            "</body></html>",
        )
        outcome = evaluate_final_response_contains(
            expected_substring="confirmed",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionPassed)
        assert (
            outcome.assertion_kind
            == "final_response_contains"
        )
        assert outcome.evidence.artifact_path == snapshot
        assert outcome.evidence.detail is not None
        assert (
            "matched substring at character offset"
            in outcome.evidence.detail
        )

    def test_evidence_includes_excerpt(self, tmp_path):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body><p>The booking is confirmed."
            "</p></body></html>",
        )
        outcome = evaluate_final_response_contains(
            expected_substring="confirmed",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionPassed)
        assert "confirmed" in outcome.evidence.detail

    def test_visible_text_match_skips_script(
        self, tmp_path
    ):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body>"
            "<script>var bookingConfirmed = true;"
            "</script>"
            "<p>The flight is booked.</p>"
            "</body></html>",
        )
        outcome = evaluate_final_response_contains(
            expected_substring="bookingConfirmed",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionFailed)

    def test_picks_highest_step_after_submit(
        self, tmp_path
    ):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body><p>old</p></body></html>",
            step_number=2,
        )
        latest = _seed_after_submit_dom(
            tmp_path,
            "<html><body>"
            "<p>booking confirmed</p>"
            "</body></html>",
            step_number=5,
        )
        outcome = evaluate_final_response_contains(
            expected_substring="confirmed",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionPassed)
        assert outcome.evidence.artifact_path == latest

    def test_unicode_substring(self, tmp_path):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body>"
            "<p>Olá, posso ajudá-lo?</p>"
            "</body></html>",
        )
        outcome = evaluate_final_response_contains(
            expected_substring="ajudá-lo",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionPassed)


class TestFailedPath:
    def test_substring_absent_returns_failed(
        self, tmp_path
    ):
        snapshot = _seed_after_submit_dom(
            tmp_path,
            "<html><body>"
            "<p>The flight is delayed</p>"
            "</body></html>",
        )
        outcome = evaluate_final_response_contains(
            expected_substring="confirmed",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionFailed)
        assert (
            outcome.assertion_kind
            == "final_response_contains"
        )
        assert outcome.expected == "confirmed"
        assert outcome.observed is not None
        assert "delayed" in outcome.observed
        assert outcome.evidence.artifact_path == snapshot

    def test_observed_truncated_for_long_text(
        self, tmp_path
    ):
        very_long = "x" * 2000
        _seed_after_submit_dom(
            tmp_path,
            f"<html><body><p>{very_long}</p>"
            "</body></html>",
        )
        outcome = evaluate_final_response_contains(
            expected_substring="banana",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionFailed)
        assert outcome.observed is not None
        assert "[...truncated]" in outcome.observed
        assert len(outcome.observed) < len(very_long)

    def test_observed_none_when_text_empty(self, tmp_path):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body>"
            "<script>not visible</script>"
            "</body></html>",
        )
        outcome = evaluate_final_response_contains(
            expected_substring="anything",
            case_dir=tmp_path,
        )
        assert isinstance(outcome, AssertionFailed)
        assert outcome.observed is None
