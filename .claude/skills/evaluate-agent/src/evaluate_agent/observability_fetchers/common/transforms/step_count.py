"""
Reduce NormalizedSpans of kind AGENT or TOOL into a canonical StepCount.
"""

from __future__ import annotations

from collections.abc import Iterable

from evaluate_agent.observability_fetchers.common.normalized_span import (
    NormalizedSpan,
    SpanKind,
)
from evaluate_agent.scoring.observability.schema import (
    StepCount,
)


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
        if span.kind is SpanKind.AGENT
    }
    candidates = sorted(
        (
            span
            for span in spans_tuple
            if span.kind in (SpanKind.AGENT, SpanKind.TOOL)
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
) -> tuple[int, str]:
    # Spans without a start_time sink to the end so the visible
    # ordering tracks the operator's mental timeline. They keep
    # a stable secondary key by virtue of Python's stable sort.
    if span.start_time:
        return (0, span.start_time)
    return (1, "")


__all__ = ["step_count_from_normalized_spans"]
