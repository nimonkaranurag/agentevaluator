"""
Evaluate the max_latency_ms assertion against the captured generation log.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
)
from evaluate_agent.scoring.resolvers.log_resolvers.generation_log import (  # noqa: E501
    generation_log_path,
    resolve_generation_log,
)

from .utils import (
    gate_generation_interval_coverage,
    resolve_observability_log,
)


def evaluate_max_latency_ms(
    latency_limit_ms: int,
    case_dir: Path,
) -> AssertionOutcome:
    log = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="max_latency_ms",
        target=None,
        needed_evidence="generation_log",
        resolve=resolve_generation_log,
        log_path=generation_log_path,
    )
    if isinstance(log, AssertionInconclusive):
        return log
    intervals = gate_generation_interval_coverage(
        log=log,
        assertion_kind="max_latency_ms",
    )
    if isinstance(intervals, AssertionInconclusive):
        return intervals
    # Wall-clock interval: earliest start to latest end across
    # the case's generations. Sum-of-per-generation latency
    # would double-count parallel sub-agent fan-out and turn a
    # 12-second wall-clock case into a 23-second false-fail
    # against a 12000ms cap.
    earliest_start = min(start for start, _ in intervals)
    latest_end = max(end for _, end in intervals)
    observed = int(
        (latest_end - earliest_start).total_seconds() * 1000
    )
    if observed <= latency_limit_ms:
        return AssertionPassed(
            assertion_kind="max_latency_ms",
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    f"observed {observed}ms wall-clock "
                    f"latency across {len(intervals)} "
                    f"generation(s) within limit of "
                    f"{latency_limit_ms}ms"
                ),
            ),
        )
    return AssertionFailed(
        assertion_kind="max_latency_ms",
        expected=f"<= {latency_limit_ms}ms",
        observed=f"{observed}ms",
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"observed {observed}ms wall-clock "
                f"latency across {len(intervals)} "
                f"generation(s) exceeding limit of "
                f"{latency_limit_ms}ms"
            ),
        ),
    )


__all__ = ["evaluate_max_latency_ms"]
