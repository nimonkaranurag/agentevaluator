"""
Coverage gate for the three generation-grounded assertions.
"""

from __future__ import annotations

from typing import Literal

from evaluate_agent.scoring.outcomes import (
    AssertionInconclusive,
    AssertionKind,
    GenerationCoverageIncomplete,
    ObservabilitySourceMissing,
)
from evaluate_agent.scoring.resolvers.log_resolvers.generation_log import (  # noqa: E501
    ResolvedGenerationLog,
)

GenerationField = Literal[
    "total_tokens",
    "total_cost_usd",
    "latency_ms",
]


def gate_generation_field_coverage(
    *,
    log: ResolvedGenerationLog,
    field_name: GenerationField,
    assertion_kind: AssertionKind,
) -> list[float] | AssertionInconclusive:
    # Empty log preserves the existing 'no generations to
    # evaluate' branch — the trace backend wrote the file but
    # captured zero generations, so the assertion has nothing to
    # bound. Same recovery path as a missing log: declare a
    # working trace backend and re-run.
    if not log.entries:
        return AssertionInconclusive(
            assertion_kind=assertion_kind,
            target=None,
            reason=ObservabilitySourceMissing(
                needed_evidence="generation_log",
                expected_artifact_path=log.path,
            ),
        )
    values = [
        getattr(entry, field_name) for entry in log.entries
    ]
    populated = sum(1 for v in values if v is not None)
    total = len(values)
    # Strict inequality: only partial coverage triggers the
    # inconclusive. Zero-population (every row missing the field)
    # is just the extreme of partial coverage and lands on the
    # same recovery instructions — far better than the previous
    # behavior, which silently summed the populated subset and
    # returned a number that looked authoritative.
    if populated < total:
        return AssertionInconclusive(
            assertion_kind=assertion_kind,
            target=None,
            reason=GenerationCoverageIncomplete(
                field=field_name,
                populated=populated,
                total=total,
                log_path=log.path,
            ),
        )
    # mypy: every entry is non-None at this point because
    # populated == total. Cast to list[float] for the caller.
    return [float(v) for v in values]


__all__ = [
    "GenerationField",
    "gate_generation_field_coverage",
]
