"""
Coverage for evaluate_max_steps across absent / malformed / pass / fail.
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
    evaluate_max_steps,
)


def _seed_step_count(case_dir: Path, payload: dict) -> Path:
    target = (
        case_dir
        / "trace"
        / "observability"
        / "step_count.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class TestAbsentLog:
    def test_inconclusive_observability_source_missing(
        self, tmp_path
    ):
        outcome = evaluate_max_steps(5, case_dir=tmp_path)
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "max_steps"
        assert outcome.target is None
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence == "step_count"
        )
        assert outcome.reason.expected_artifact_path == (
            tmp_path
            / "trace"
            / "observability"
            / "step_count.json"
        )


class TestMalformedLog:
    def test_inconclusive_log_malformed(self, tmp_path):
        target = (
            tmp_path
            / "trace"
            / "observability"
            / "step_count.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{nope", encoding="utf-8")
        outcome = evaluate_max_steps(5, case_dir=tmp_path)
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, ObservabilityLogMalformed
        )
        assert outcome.reason.log_path == target
        assert outcome.reason.line_number is None

    def test_inconclusive_schema_violation(self, tmp_path):
        _seed_step_count(
            tmp_path,
            {
                "total_steps": 5,
                "step_span_ids": ["only_one"],
            },
        )
        outcome = evaluate_max_steps(5, case_dir=tmp_path)
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, ObservabilityLogMalformed
        )


class TestPassPath:
    def test_steps_within_limit_passes(self, tmp_path):
        target = _seed_step_count(
            tmp_path,
            {
                "total_steps": 3,
                "step_span_ids": ["a", "b", "c"],
            },
        )
        outcome = evaluate_max_steps(5, case_dir=tmp_path)
        assert isinstance(outcome, AssertionPassed)
        assert outcome.evidence.artifact_path == target
        assert "3 step" in outcome.evidence.detail
        assert "limit of 5" in outcome.evidence.detail

    def test_steps_at_limit_passes(self, tmp_path):
        _seed_step_count(
            tmp_path,
            {
                "total_steps": 5,
                "step_span_ids": ["a", "b", "c", "d", "e"],
            },
        )
        outcome = evaluate_max_steps(5, case_dir=tmp_path)
        assert isinstance(outcome, AssertionPassed)

    def test_zero_steps_passes(self, tmp_path):
        _seed_step_count(
            tmp_path,
            {"total_steps": 0, "step_span_ids": []},
        )
        outcome = evaluate_max_steps(5, case_dir=tmp_path)
        assert isinstance(outcome, AssertionPassed)


class TestFailPath:
    def test_steps_over_limit_fails(self, tmp_path):
        target = _seed_step_count(
            tmp_path,
            {
                "total_steps": 7,
                "step_span_ids": [
                    "a",
                    "b",
                    "c",
                    "d",
                    "e",
                    "f",
                    "g",
                ],
            },
        )
        outcome = evaluate_max_steps(5, case_dir=tmp_path)
        assert isinstance(outcome, AssertionFailed)
        assert outcome.expected == "<= 5"
        assert outcome.observed == "7"
        assert outcome.evidence.artifact_path == target
        assert (
            "exceeding limit of 5"
            in outcome.evidence.detail
        )
