"""
Cross-source result type returned by every observability-fetcher implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .writer import WrittenObservabilityArtifacts


@dataclass(frozen=True)
class FetchedObservability:
    # Base URL of the backend the fetch executed against —
    # `https://cloud.langfuse.com` for LangFuse, the Tempo-style
    # query base (e.g. `https://tempo.example.com`) for OTEL.
    endpoint: str
    session_id: str
    trace_ids: tuple[str, ...]
    observation_count: int
    tool_call_count: int
    routing_decision_count: int
    step_count_total: int
    generation_count: int
    generations_with_tokens: int
    generations_with_cost: int
    generations_with_interval: int
    total_tokens: int | None
    total_cost_usd: float | None
    written: WrittenObservabilityArtifacts


__all__ = ["FetchedObservability"]
