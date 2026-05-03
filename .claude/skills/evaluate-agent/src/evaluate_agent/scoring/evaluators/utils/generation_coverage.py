"""
Coverage gates for the generation-grounded assertions.
"""

from __future__ import annotations

from datetime import datetime
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


def gate_generation_interval_coverage(
    *,
    log: ResolvedGenerationLog,
    assertion_kind: AssertionKind,
) -> (
    list[tuple[datetime, datetime]] | AssertionInconclusive
):
    # Wall-clock latency anchors on every generation's
    # started_at AND ended_at. Treating the pair as a single
    # 'interval' coverage signal keeps the inconclusive surface
    # symmetric with the field-level gate above: any row missing
    # either bound disqualifies the whole case from a wall-clock
    # answer, so a partial interval and a partial sum-field are
    # both rendered as "GenerationCoverageIncomplete".
    if not log.entries:
        return AssertionInconclusive(
            assertion_kind=assertion_kind,
            target=None,
            reason=ObservabilitySourceMissing(
                needed_evidence="generation_log",
                expected_artifact_path=log.path,
            ),
        )
    intervals: list[tuple[datetime, datetime] | None] = []
    for entry in log.entries:
        start_dt = _parse_iso_or_none(entry.started_at)
        end_dt = _parse_iso_or_none(entry.ended_at)
        if start_dt is None or end_dt is None:
            intervals.append(None)
            continue
        # An end-before-start interval is data corruption, not
        # partial coverage — but it would make max(end) -
        # min(start) implicitly negative and the assertion
        # always pass. Treat as missing instead so the operator
        # is told to fix the trace.
        if end_dt < start_dt:
            intervals.append(None)
            continue
        intervals.append((start_dt, end_dt))
    populated = sum(1 for i in intervals if i is not None)
    total = len(intervals)
    if populated < total:
        return AssertionInconclusive(
            assertion_kind=assertion_kind,
            target=None,
            reason=GenerationCoverageIncomplete(
                field="interval",
                populated=populated,
                total=total,
                log_path=log.path,
            ),
        )
    # mypy: every entry is non-None at this point because
    # populated == total.
    return [i for i in intervals if i is not None]


def _parse_iso_or_none(
    value: str | None,
) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None


__all__ = [
    "GenerationField",
    "gate_generation_field_coverage",
    "gate_generation_interval_coverage",
]
