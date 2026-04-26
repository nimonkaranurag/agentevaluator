"""
Coverage for evaluate_must_route_to across absent / malformed / pass / fail.
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
    evaluate_must_route_to,
)


def _seed_routing(
    case_dir: Path, lines: list[dict]
) -> Path:
    target = (
        case_dir
        / "trace"
        / "observability"
        / "routing_decisions.jsonl"
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
        outcome = evaluate_must_route_to(
            "billing_specialist", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "must_route_to"
        assert outcome.target == "billing_specialist"
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence
            == "routing_decision_log"
        )
        assert outcome.reason.expected_artifact_path == (
            tmp_path
            / "trace"
            / "observability"
            / "routing_decisions.jsonl"
        )


class TestMalformedLog:
    def test_inconclusive_log_malformed(self, tmp_path):
        target = (
            tmp_path
            / "trace"
            / "observability"
            / "routing_decisions.jsonl"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '{"target_agent": "ok"}\n',
            encoding="utf-8",
        )
        outcome = evaluate_must_route_to(
            "billing_specialist", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert isinstance(
            outcome.reason, ObservabilityLogMalformed
        )
        assert outcome.reason.log_path == target


class TestPassPath:
    def test_first_match_passes(self, tmp_path):
        target = _seed_routing(
            tmp_path,
            [
                {
                    "target_agent": "tier1_support",
                    "span_id": "r1",
                },
                {
                    "target_agent": "billing_specialist",
                    "span_id": "r2",
                },
            ],
        )
        outcome = evaluate_must_route_to(
            "billing_specialist", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionPassed)
        assert outcome.evidence.artifact_path == target
        detail = outcome.evidence.detail
        assert "line 2" in detail
        assert "span_id=r2" in detail


class TestFailPath:
    def test_target_not_in_log_fails(self, tmp_path):
        target = _seed_routing(
            tmp_path,
            [
                {
                    "target_agent": "tier1_support",
                    "span_id": "r1",
                },
                {
                    "target_agent": "tier2_support",
                    "span_id": "r2",
                },
            ],
        )
        outcome = evaluate_must_route_to(
            "billing_specialist", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert outcome.expected == "billing_specialist"
        assert outcome.observed is not None
        assert "tier1_support" in outcome.observed
        assert "tier2_support" in outcome.observed
        assert outcome.evidence.artifact_path == target

    def test_empty_log_fails(self, tmp_path):
        target = _seed_routing(tmp_path, [])
        outcome = evaluate_must_route_to(
            "billing_specialist", case_dir=tmp_path
        )
        assert isinstance(outcome, AssertionFailed)
        assert outcome.observed is None
        assert outcome.evidence.artifact_path == target
