"""
Failure-mode tests for the generation-grounded evaluators (max_total_tokens, max_total_cost_usd, max_latency_ms) and the coverage gates they share.
"""

from __future__ import annotations

from pathlib import Path

from conftest import write_generations
from evaluate_agent.scoring.evaluators import (
    evaluate_max_latency_ms,
    evaluate_max_total_cost_usd,
    evaluate_max_total_tokens,
)
from evaluate_agent.scoring.outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    GenerationCoverageIncomplete,
    ObservabilitySourceMissing,
)


def test_max_total_tokens_inconclusive_when_log_absent(
    case_dir: Path,
) -> None:
    outcome = evaluate_max_total_tokens(1000, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, ObservabilitySourceMissing
    )


def test_max_total_tokens_inconclusive_when_log_empty(
    case_dir: Path,
) -> None:
    # Empty log: backend wrote the file, captured zero generations.
    # The recovery path is identical to "log absent" — declare a
    # working trace backend and re-run — so the inconclusive
    # surfaces as ObservabilitySourceMissing rather than partial
    # coverage.
    write_generations(case_dir, [])
    outcome = evaluate_max_total_tokens(1000, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, ObservabilitySourceMissing
    )


def test_max_total_tokens_inconclusive_on_partial_coverage(
    case_dir: Path,
) -> None:
    # Partial coverage MUST resolve to inconclusive — silently
    # summing the populated subset would produce a false-pass
    # against incomplete evidence. This is the signal max_total_*
    # gates exist for.
    write_generations(
        case_dir,
        [
            {"span_id": "g1", "total_tokens": 500},
            {"span_id": "g2"},  # missing total_tokens
        ],
    )
    outcome = evaluate_max_total_tokens(1000, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, GenerationCoverageIncomplete
    )
    assert outcome.reason.field == "total_tokens"
    assert outcome.reason.populated == 1
    assert outcome.reason.total == 2


def test_max_total_tokens_passes_at_inclusive_limit(
    case_dir: Path,
) -> None:
    write_generations(
        case_dir,
        [
            {"span_id": "g1", "total_tokens": 600},
            {"span_id": "g2", "total_tokens": 400},
        ],
    )
    outcome = evaluate_max_total_tokens(1000, case_dir)
    assert isinstance(outcome, AssertionPassed)


def test_max_total_tokens_fails_when_sum_exceeds(
    case_dir: Path,
) -> None:
    write_generations(
        case_dir,
        [
            {"span_id": "g1", "total_tokens": 800},
            {"span_id": "g2", "total_tokens": 300},
        ],
    )
    outcome = evaluate_max_total_tokens(1000, case_dir)
    assert isinstance(outcome, AssertionFailed)
    assert outcome.observed == "1100"


def test_max_total_cost_inconclusive_when_no_cost_emitted(
    case_dir: Path,
) -> None:
    # Self-hosted LangFuse instances often skip cost mapping —
    # every row carries total_cost_usd=null. The gate must
    # treat zero-population the same as partial: an inconclusive
    # naming the missing field, not a $0.00 false-pass.
    write_generations(
        case_dir,
        [
            {"span_id": "g1", "total_tokens": 500},
            {"span_id": "g2", "total_tokens": 500},
        ],
    )
    outcome = evaluate_max_total_cost_usd(0.10, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, GenerationCoverageIncomplete
    )
    assert outcome.reason.field == "total_cost_usd"
    assert outcome.reason.populated == 0


def test_max_total_cost_passes_within_budget(
    case_dir: Path,
) -> None:
    write_generations(
        case_dir,
        [
            {"span_id": "g1", "total_cost_usd": 0.02},
            {"span_id": "g2", "total_cost_usd": 0.03},
        ],
    )
    outcome = evaluate_max_total_cost_usd(0.10, case_dir)
    assert isinstance(outcome, AssertionPassed)


def test_max_total_cost_fails_when_sum_exceeds_budget(
    case_dir: Path,
) -> None:
    write_generations(
        case_dir,
        [
            {"span_id": "g1", "total_cost_usd": 0.06},
            {"span_id": "g2", "total_cost_usd": 0.05},
        ],
    )
    outcome = evaluate_max_total_cost_usd(0.10, case_dir)
    assert isinstance(outcome, AssertionFailed)


def test_max_latency_inconclusive_on_missing_interval(
    case_dir: Path,
) -> None:
    # If any generation lacks started_at OR ended_at, the case's
    # wall-clock interval is uncomputable. The gate surfaces
    # this as GenerationCoverageIncomplete(field='interval')
    # rather than computing a wrong-shaped maximum on the
    # populated subset.
    write_generations(
        case_dir,
        [
            {
                "span_id": "g1",
                "started_at": "2026-04-25T17:30:00Z",
                "ended_at": "2026-04-25T17:30:05Z",
            },
            {
                "span_id": "g2",
                "started_at": "2026-04-25T17:30:02Z",
                # ended_at missing
            },
        ],
    )
    outcome = evaluate_max_latency_ms(20000, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, GenerationCoverageIncomplete
    )
    assert outcome.reason.field == "interval"


def test_max_latency_inconclusive_on_inverted_interval(
    case_dir: Path,
) -> None:
    # ended_at < started_at is data corruption, not partial
    # coverage. Treating it as missing surfaces the trace bug
    # to the operator instead of letting max(end) - min(start)
    # silently compute a negative or near-zero latency that
    # would always pass.
    write_generations(
        case_dir,
        [
            {
                "span_id": "g1",
                "started_at": "2026-04-25T17:30:10Z",
                "ended_at": "2026-04-25T17:30:00Z",
            },
        ],
    )
    outcome = evaluate_max_latency_ms(5000, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, GenerationCoverageIncomplete
    )


def test_max_latency_anchors_on_wall_clock_interval(
    case_dir: Path,
) -> None:
    # Two parallel sub-agent generations: g1 from 0s-5s,
    # g2 from 2s-8s. Sum-of-per-generation latency would
    # report 5+6=11s. The wall-clock anchor reports 8s —
    # max(end) - min(start). This is the documented contract.
    write_generations(
        case_dir,
        [
            {
                "span_id": "g1",
                "started_at": "2026-04-25T17:30:00Z",
                "ended_at": "2026-04-25T17:30:05Z",
            },
            {
                "span_id": "g2",
                "started_at": "2026-04-25T17:30:02Z",
                "ended_at": "2026-04-25T17:30:08Z",
            },
        ],
    )
    outcome = evaluate_max_latency_ms(8000, case_dir)
    assert isinstance(outcome, AssertionPassed)
    # 8000ms exactly is the boundary — passes inclusively.
    assert "8000ms" in outcome.evidence.detail


def test_max_latency_fails_when_wall_clock_exceeds_limit(
    case_dir: Path,
) -> None:
    write_generations(
        case_dir,
        [
            {
                "span_id": "g1",
                "started_at": "2026-04-25T17:30:00Z",
                "ended_at": "2026-04-25T17:30:10Z",
            },
        ],
    )
    outcome = evaluate_max_latency_ms(5000, case_dir)
    assert isinstance(outcome, AssertionFailed)
    assert outcome.observed == "10000ms"


def test_max_latency_inconclusive_on_unparseable_iso_timestamp(
    case_dir: Path,
) -> None:
    # Treat unparseable timestamps as missing so the operator
    # learns the trace shape is wrong, instead of silently
    # passing on the populated subset.
    write_generations(
        case_dir,
        [
            {
                "span_id": "g1",
                "started_at": "not-a-timestamp",
                "ended_at": "2026-04-25T17:30:05Z",
            },
        ],
    )
    outcome = evaluate_max_latency_ms(20000, case_dir)
    assert isinstance(outcome, AssertionInconclusive)
