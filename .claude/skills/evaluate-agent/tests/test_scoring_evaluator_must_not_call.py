"""
Coverage for evaluate_must_not_call across absent / malformed / pass / fail.
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
    evaluate_must_not_call,
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
        outcome = evaluate_must_not_call(
            "delete_account", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "must_not_call"
        assert outcome.target == "delete_account"
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence
            == "tool_call_log"
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
        target.write_text("{not-json", encoding="utf-8")
        outcome = evaluate_must_not_call(
            "delete_account", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, ObservabilityLogMalformed
        )
        assert outcome.reason.log_path == target


class TestPassPath:
    def test_target_absent_passes(self, tmp_path):
        target = _seed_tool_calls(
            tmp_path,
            [
                {
                    "tool_name": "search",
                    "span_id": "s1",
                },
                {
                    "tool_name": "transfer",
                    "span_id": "s2",
                },
            ],
        )
        outcome = evaluate_must_not_call(
            "delete_account", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionPassed)
        assert outcome.evidence.artifact_path == target
        assert (
            "2 logged tool call" in outcome.evidence.detail
        )

    def test_empty_log_passes(self, tmp_path):
        _seed_tool_calls(tmp_path, [])
        outcome = evaluate_must_not_call(
            "delete_account", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionPassed)
        assert (
            "0 logged tool call" in outcome.evidence.detail
        )


class TestFailPath:
    def test_first_forbidden_call_fails(self, tmp_path):
        target = _seed_tool_calls(
            tmp_path,
            [
                {
                    "tool_name": "search",
                    "span_id": "s1",
                },
                {
                    "tool_name": "delete_account",
                    "span_id": "danger-1",
                },
                {
                    "tool_name": "delete_account",
                    "span_id": "danger-2",
                },
            ],
        )
        outcome = evaluate_must_not_call(
            "delete_account", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert "delete_account" in outcome.expected
        assert outcome.observed == "delete_account"
        assert outcome.evidence.artifact_path == target
        detail = outcome.evidence.detail
        assert "line 2" in detail
        assert "span_id=danger-1" in detail
