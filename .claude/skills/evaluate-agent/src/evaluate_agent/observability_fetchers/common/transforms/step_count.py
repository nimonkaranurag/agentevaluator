"""
Reduce AgentSpans and ToolSpans into a canonical StepCount.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from evaluate_agent.observability_fetchers.common.normalized_span import (
    AgentSpan,
    NormalizedSpan,
    ToolSpan,
)
from evaluate_agent.scoring.observability.schema import (
    StepCount,
)

_FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


def step_count_from_normalized_spans(
    spans: Iterable[NormalizedSpan],
) -> StepCount:
    # A reasoning step is one AGENT or TOOL span the agent
    # dispatched directly — i.e. whose parent is either the
    # trace root or another AGENT span. This excludes nested
    # TOOL-under-TOOL retries and intermediate GENERATIONs
    # (which are LLM calls inside a step, not steps themselves),
    # matching how operators count steps when reading a trace
    # tree.
    spans_tuple = tuple(spans)
    agent_span_ids = {
        span.span_id
        for span in spans_tuple
        if isinstance(span, AgentSpan)
    }
    candidates = sorted(
        (
            span
            for span in spans_tuple
            if isinstance(span, (AgentSpan, ToolSpan))
            and (
                span.parent_span_id is None
                or span.parent_span_id in agent_span_ids
            )
        ),
        key=_start_time_sort_key,
    )
    span_ids = tuple(span.span_id for span in candidates)
    return StepCount(
        total_steps=len(span_ids),
        step_span_ids=span_ids,
    )


def _start_time_sort_key(
    span: NormalizedSpan,
) -> tuple[int, datetime]:
    # Parse to datetime instead of comparing ISO strings:
    # lexicographic sort of ISO-8601 only happens to work when
    # every timestamp uses the same fractional-seconds format
    # and the same TZ representation, which is not guaranteed
    # across LangFuse / OTEL emitters or even within a single
    # mixed-version backend. Spans without a parseable start
    # sink to the end via the (1, _FAR_FUTURE) bucket so the
    # sort remains total.
    if not span.start_time:
        return (1, _FAR_FUTURE)
    try:
        parsed = datetime.fromisoformat(span.start_time)
    except ValueError:
        return (1, _FAR_FUTURE)
    if parsed.tzinfo is None:
        # Naive timestamps from a backend that doesn't stamp TZ
        # are interpreted as UTC, matching how our normalizers
        # serialise OTEL unix-nano values.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (0, parsed)


__all__ = ["step_count_from_normalized_spans"]
