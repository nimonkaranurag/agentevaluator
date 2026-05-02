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
    ObservabilitySourceMissing,
)
from evaluate_agent.scoring.resolvers.log_resolvers.generation_log import (  # noqa: E501
    generation_log_path,
    resolve_generation_log,
)

from .utils import resolve_observability_log


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
    contributions = [
        entry.latency_ms
        for entry in log.entries
        if entry.latency_ms is not None
    ]
    if not contributions:
        return AssertionInconclusive(
            assertion_kind="max_latency_ms",
            target=None,
            reason=ObservabilitySourceMissing(
                needed_evidence="generation_log",
                expected_artifact_path=log.path,
            ),
        )
    observed = sum(contributions)
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
