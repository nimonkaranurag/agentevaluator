"""
Failure-mode tests for evaluate_must_route_to and evaluate_max_steps.
"""

from __future__ import annotations

from pathlib import Path

from conftest import (
    write_routing_decisions,
    write_step_count,
)
from evaluate_agent.scoring.evaluators import (
    evaluate_max_steps,
    evaluate_must_route_to,
)
from evaluate_agent.scoring.outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)


def test_must_route_to_inconclusive_without_log(
    case_dir: Path,
) -> None:
    outcome = evaluate_must_route_to("billing", case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, ObservabilitySourceMissing
    )
    assert (
        outcome.reason.needed_evidence
        == "routing_decision_log"
    )


def test_must_route_to_passes_on_match(
    case_dir: Path,
) -> None:
    write_routing_decisions(
        case_dir,
        [
            {"target_agent": "support", "span_id": "r1"},
            {"target_agent": "billing", "span_id": "r2"},
        ],
    )
    outcome = evaluate_must_route_to("billing", case_dir)
    assert isinstance(outcome, AssertionPassed)
    assert "line 2" in outcome.evidence.detail


def test_must_route_to_fails_with_observed_targets(
    case_dir: Path,
) -> None:
    # Failure surfaces every observed target so the operator
    # sees the actual routing topology and can decide whether
    # the assertion or the agent is wrong.
    write_routing_decisions(
        case_dir,
        [
            {"target_agent": "support", "span_id": "r1"},
            {"target_agent": "support", "span_id": "r2"},
        ],
    )
    outcome = evaluate_must_route_to("billing", case_dir)
    assert isinstance(outcome, AssertionFailed)
    assert outcome.observed == "support"


def test_max_steps_inconclusive_without_record(
    case_dir: Path,
) -> None:
    outcome = evaluate_max_steps(5, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert outcome.reason.needed_evidence == "step_count"


def test_max_steps_passes_at_inclusive_limit(
    case_dir: Path,
) -> None:
    # The limit is inclusive — observed == limit MUST pass.
    # Otherwise the operator can never declare a tight bound
    # they actually want to enforce.
    write_step_count(
        case_dir,
        {
            "total_steps": 5,
            "step_span_ids": ["a", "b", "c", "d", "e"],
        },
    )
    outcome = evaluate_max_steps(5, case_dir)
    assert isinstance(outcome, AssertionPassed)


def test_max_steps_fails_when_observed_exceeds_limit(
    case_dir: Path,
) -> None:
    write_step_count(
        case_dir,
        {
            "total_steps": 6,
            "step_span_ids": [
                "a",
                "b",
                "c",
                "d",
                "e",
                "f",
            ],
        },
    )
    outcome = evaluate_max_steps(5, case_dir)
    assert isinstance(outcome, AssertionFailed)
    assert outcome.expected == "<= 5"
    assert outcome.observed == "6"


def test_max_steps_inconclusive_when_record_malformed(
    case_dir: Path,
) -> None:
    # total_steps and step_span_ids length must match — if the
    # fetcher emits an inconsistent record, the evaluator turns
    # the underlying ObservabilityLogMalformedError into an
    # inconclusive with the recovery procedure inline.
    write_step_count(
        case_dir,
        {"total_steps": 3, "step_span_ids": ["a"]},
    )
    outcome = evaluate_max_steps(5, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, ObservabilityLogMalformed
    )
