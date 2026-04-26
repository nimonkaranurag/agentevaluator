"""
Coverage for evaluate_no_uncaught_page_errors across absent / malformed / pass / fail.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluate_agent.scoring import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    BaselineTraceArtifactMissing,
    BaselineTraceLogMalformed,
    evaluate_no_uncaught_page_errors,
)


def _seed_page_errors(
    case_dir: Path, lines: list[dict]
) -> Path:
    target = case_dir / "trace" / "page_errors.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(line) for line in lines),
        encoding="utf-8",
    )
    return target


class TestAbsentLog:
    def test_inconclusive_baseline_artifact_missing(
        self, tmp_path
    ):
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert (
            outcome.assertion_kind
            == "no_uncaught_page_errors"
        )
        assert outcome.target is None
        assert isinstance(
            outcome.reason, BaselineTraceArtifactMissing
        )
        assert (
            outcome.reason.needed_artifact
            == "page_errors_log"
        )
        assert outcome.reason.expected_artifact_path == (
            tmp_path / "trace" / "page_errors.jsonl"
        )
        assert "open_agent.py" in outcome.reason.recovery


class TestMalformedLog:
    def test_inconclusive_when_invalid_json(self, tmp_path):
        target = tmp_path / "trace" / "page_errors.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '{"ts": "ok", "message": "ok"}\n'
            "not-json-at-all\n",
            encoding="utf-8",
        )
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, BaselineTraceLogMalformed
        )
        assert outcome.reason.log_path == target
        assert outcome.reason.line_number == 2
        assert "invalid JSON" in outcome.reason.parse_error

    def test_inconclusive_when_schema_violation(
        self, tmp_path
    ):
        target = _seed_page_errors(
            tmp_path,
            [
                {
                    "ts": "2026-04-26T12:00:00.000+00:00",
                    "message": "ok",
                },
                {"ts": "2026-04-26T12:00:01.000+00:00"},
            ],
        )
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, BaselineTraceLogMalformed
        )
        assert outcome.reason.line_number == 2
        assert outcome.reason.log_path == target
        assert (
            "schema violation" in outcome.reason.parse_error
        )
        assert (
            "PageErrorEntry" in outcome.reason.parse_error
        )


class TestPassPath:
    def test_empty_log_passes(self, tmp_path):
        target = _seed_page_errors(tmp_path, [])
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionPassed)
        assert (
            outcome.assertion_kind
            == "no_uncaught_page_errors"
        )
        assert outcome.target is None
        assert outcome.evidence.artifact_path == target
        assert (
            "no uncaught page errors"
            in outcome.evidence.detail
        )

    def test_passed_carries_no_observed(self, tmp_path):
        _seed_page_errors(tmp_path, [])
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionPassed)
        assert not hasattr(outcome, "observed")


class TestFailPath:
    def test_single_error_fails_citing_first(
        self, tmp_path
    ):
        target = _seed_page_errors(
            tmp_path,
            [
                {
                    "ts": "2026-04-26T12:00:00.000+00:00",
                    "message": (
                        "ReferenceError: x is not defined"
                    ),
                }
            ],
        )
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert (
            outcome.expected == "zero uncaught page errors"
        )
        assert outcome.observed == (
            "ReferenceError: x is not defined"
        )
        assert outcome.evidence.artifact_path == target
        detail = outcome.evidence.detail
        assert "line 1" in detail
        assert "ts=2026-04-26T12:00:00.000+00:00" in detail
        assert "1 total uncaught error(s)" in detail

    def test_multiple_errors_cites_first_only(
        self, tmp_path
    ):
        _seed_page_errors(
            tmp_path,
            [
                {
                    "ts": "2026-04-26T12:00:00.000+00:00",
                    "message": "first error",
                },
                {
                    "ts": "2026-04-26T12:00:01.000+00:00",
                    "message": "second error",
                },
                {
                    "ts": "2026-04-26T12:00:02.000+00:00",
                    "message": "third error",
                },
            ],
        )
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert outcome.observed == "first error"
        assert (
            "3 total uncaught error(s)"
            in outcome.evidence.detail
        )

    def test_long_message_truncates_observed(
        self, tmp_path
    ):
        long_message = "X" * 500
        _seed_page_errors(
            tmp_path,
            [
                {
                    "ts": "2026-04-26T12:00:00.000+00:00",
                    "message": long_message,
                }
            ],
        )
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert "[...truncated]" in outcome.observed
        assert len(outcome.observed) < len(long_message)

    def test_short_message_not_truncated(self, tmp_path):
        _seed_page_errors(
            tmp_path,
            [
                {
                    "ts": "2026-04-26T12:00:00.000+00:00",
                    "message": "TypeError: a.b is null",
                }
            ],
        )
        outcome = evaluate_no_uncaught_page_errors(
            case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert "[...truncated]" not in outcome.observed
        assert outcome.observed == (
            "TypeError: a.b is null"
        )
