"""
Shared tail of every per-source fetcher: project spans, persist artifacts, summarise stats.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from evaluate_agent.observability_fetchers.fetcher import (
    FetchedObservability,
)
from evaluate_agent.observability_fetchers.writer import (
    write_observability_artifacts,
)

from .fetch_context import FetchContext
from .normalized_span import NormalizedSpan
from .stats import aggregate_generation_stats
from .transforms import (
    generations_from_normalized_spans,
    routing_decisions_from_normalized_spans,
    step_count_from_normalized_spans,
    tool_calls_from_normalized_spans,
)


def assemble_fetched_observability(
    spans: Iterable[NormalizedSpan],
    *,
    context: FetchContext,
    trace_ids: Sequence[str],
) -> FetchedObservability:
    # Per-source code is responsible only for credentials,
    # network I/O, and the source-specific normalize step. Once
    # spans are in the canonical NormalizedSpan shape, the
    # projections to ToolCall / RoutingDecision / StepCount /
    # Generation, the write to disk, and the stats aggregation
    # are identical across every backend.
    spans_tuple = tuple(spans)
    tool_calls = tool_calls_from_normalized_spans(
        spans_tuple
    )
    routing_decisions = (
        routing_decisions_from_normalized_spans(spans_tuple)
    )
    step_count = step_count_from_normalized_spans(
        spans_tuple
    )
    generations = generations_from_normalized_spans(
        spans_tuple
    )

    written = write_observability_artifacts(
        case_dir=context.case_dir,
        tool_calls=tool_calls,
        routing_decisions=routing_decisions,
        step_count=step_count,
        generations=generations,
    )

    stats = aggregate_generation_stats(generations)
    return FetchedObservability(
        endpoint=context.endpoint,
        session_id=context.session_id,
        trace_ids=tuple(trace_ids),
        observation_count=len(spans_tuple),
        tool_call_count=len(tool_calls),
        routing_decision_count=len(routing_decisions),
        step_count_total=step_count.total_steps,
        generation_count=len(generations),
        generations_with_tokens=stats.with_tokens,
        generations_with_cost=stats.with_cost,
        generations_with_interval=stats.with_interval,
        total_tokens=stats.total_tokens,
        total_cost_usd=stats.total_cost_usd,
        written=written,
    )


__all__ = ["assemble_fetched_observability"]
