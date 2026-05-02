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
    gate_generation_field_coverage,
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
    # Coverage gate before sum: latency_ms is derived from the
    # span's start_time / end_time, and traces with broken
    # clocks or partial timestamping would otherwise undercount
    # silently. Note: this still uses sum-of-per-generation
    # latency, which double-counts parallel fan-out — that's
    # tracked as a separate Session 4 fix (max latency should
    # be wall-clock span, not sum).
    contributions = gate_generation_field_coverage(
        log=log,
        field_name="latency_ms",
        assertion_kind="max_latency_ms",
    )
    if isinstance(contributions, AssertionInconclusive):
        return contributions
    observed = int(sum(contributions))
    if observed <= latency_limit_ms:
        return AssertionPassed(
            assertion_kind="max_latency_ms",
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    f"observed {observed}ms total "
                    f"generation latency across "
                    f"{len(contributions)} "
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
                f"observed {observed}ms total "
                f"generation latency across "
                f"{len(contributions)} "
                f"generation(s) exceeding limit of "
                f"{latency_limit_ms}ms"
            ),
        ),
    )


__all__ = ["evaluate_max_latency_ms"]
