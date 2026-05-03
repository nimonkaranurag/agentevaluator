"""
Project GenerationSpans onto canonical Generation records.
"""

from __future__ import annotations

from collections.abc import Iterable

from evaluate_agent.observability_fetchers.common.normalized_span import (
    GenerationSpan,
    NormalizedSpan,
)
from evaluate_agent.scoring.observability.schema import (
    Generation,
)


def generations_from_normalized_spans(
    spans: Iterable[NormalizedSpan],
) -> tuple[Generation, ...]:
    return tuple(
        Generation(
            span_id=span.span_id,
            model=span.model,
            input_tokens=span.input_tokens,
            output_tokens=span.output_tokens,
            total_tokens=span.total_tokens,
            input_cost_usd=span.input_cost_usd,
            output_cost_usd=span.output_cost_usd,
            total_cost_usd=span.total_cost_usd,
            started_at=span.start_time,
            ended_at=span.end_time,
        )
        for span in spans
        if isinstance(span, GenerationSpan)
    )


__all__ = ["generations_from_normalized_spans"]
