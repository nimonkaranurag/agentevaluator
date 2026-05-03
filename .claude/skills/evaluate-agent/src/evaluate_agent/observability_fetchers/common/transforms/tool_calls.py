"""
Project ToolSpans onto canonical ToolCall records.
"""

from __future__ import annotations

from collections.abc import Iterable

from evaluate_agent.observability_fetchers.common.normalized_span import (
    NormalizedSpan,
    ToolSpan,
)
from evaluate_agent.scoring.observability.schema import (
    ToolCall,
)


def tool_calls_from_normalized_spans(
    spans: Iterable[NormalizedSpan],
) -> tuple[ToolCall, ...]:
    return tuple(
        ToolCall(
            tool_name=span.name,
            span_id=span.span_id,
            arguments=span.input,
            result=span.output,
            timestamp=span.start_time,
        )
        for span in spans
        if isinstance(span, ToolSpan) and span.name
    )


__all__ = ["tool_calls_from_normalized_spans"]
