"""
Project NormalizedSpans of kind AGENT onto canonical RoutingDecision records.
"""

from __future__ import annotations

from collections.abc import Iterable

from evaluate_agent.observability_fetchers.common.normalized_span import (
    NormalizedSpan,
    SpanKind,
)
from evaluate_agent.scoring.observability.schema import (
    RoutingDecision,
)


def routing_decisions_from_normalized_spans(
    spans: Iterable[NormalizedSpan],
) -> tuple[RoutingDecision, ...]:
    spans_tuple = tuple(spans)
    parent_agent_name_by_id = {
        span.span_id: span.name
        for span in spans_tuple
        if span.kind is SpanKind.AGENT
    }
    return tuple(
        RoutingDecision(
            target_agent=span.name,
            span_id=span.span_id,
            from_agent=parent_agent_name_by_id.get(
                span.parent_span_id
            ),
            reason=span.routing_reason,
            timestamp=span.start_time,
        )
        for span in spans_tuple
        if span.kind is SpanKind.AGENT and span.name
    )


__all__ = ["routing_decisions_from_normalized_spans"]
