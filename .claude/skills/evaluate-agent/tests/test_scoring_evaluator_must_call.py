"""
Coverage for evaluate_must_call across absent / malformed / pass / fail.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluate_agent.scoring import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
    evaluate_must_call,
)


def _seed_tool_calls(
    case_dir: Path, lines: list[dict]
) -> Path:
    target = (
        case_dir
        / "trace"
        / "observability"
        / "tool_calls.jsonl"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(line) for line in lines),
        encoding="utf-8",
    )
    return target


class TestAbsentLog:
    def test_inconclusive_observability_source_missing(
        self, tmp_path
    ):
        outcome = evaluate_must_call(
            "search", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "must_call"
        assert outcome.target == "search"
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence
            == "tool_call_log"
        )
        assert outcome.reason.expected_artifact_path == (
            tmp_path
            / "trace"
            / "observability"
            / "tool_calls.jsonl"
        )


class TestMalformedLog:
    def test_inconclusive_log_malformed(self, tmp_path):
        target = (
            tmp_path
            / "trace"
            / "observability"
            / "tool_calls.jsonl"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "totally-not-json\n", encoding="utf-8"
        )
        outcome = evaluate_must_call(
            "search", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, ObservabilityLogMalformed
        )
        assert outcome.reason.log_path == target
        assert outcome.reason.line_number == 1
        assert "invalid JSON" in outcome.reason.parse_error

    def test_inconclusive_schema_violation(self, tmp_path):
        target = _seed_tool_calls(
            tmp_path, [{"tool_name": "ok"}]
        )
        outcome = evaluate_must_call(
            "search", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, ObservabilityLogMalformed
        )
        assert outcome.reason.line_number == 1
        assert (
            "schema violation" in outcome.reason.parse_error
        )


class TestPassPath:
    def test_first_match_passes(self, tmp_path):
        target = _seed_tool_calls(
            tmp_path,
            [
                {
                    "tool_name": "lookup_pix",
                    "span_id": "s1",
                },
                {
                    "tool_name": "search",
                    "span_id": "s2",
                },
                {
                    "tool_name": "search",
                    "span_id": "s3",
                },
            ],
        )
        outcome = evaluate_must_call(
            "search", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionPassed)
        assert outcome.evidence.artifact_path == target
        detail = outcome.evidence.detail
        assert "line 2" in detail
        assert "span_id=s2" in detail


class TestFailPath:
    def test_no_calls_logged_fails(self, tmp_path):
        target = _seed_tool_calls(tmp_path, [])
        outcome = evaluate_must_call(
            "search", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert outcome.expected == "search"
        assert outcome.observed is None
        assert outcome.evidence.artifact_path == target
        assert (
            "0 logged tool call" in outcome.evidence.detail
        )

    def test_target_not_in_log_fails(self, tmp_path):
        target = _seed_tool_calls(
            tmp_path,
            [
                {
                    "tool_name": "transfer",
                    "span_id": "s1",
                },
                {
                    "tool_name": "lookup_pix",
                    "span_id": "s2",
                },
            ],
        )
        outcome = evaluate_must_call(
            "search", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert outcome.expected == "search"
        assert outcome.observed is not None
        assert "transfer" in outcome.observed
        assert "lookup_pix" in outcome.observed
        assert outcome.evidence.artifact_path == target
