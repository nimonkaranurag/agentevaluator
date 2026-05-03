"""
Discriminated union of normalized spans, one variant per kind the canonical schema cares about.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias


@dataclass(frozen=True)
class _SpanCommon:
    # The span's stable identifier within its source backend.
    # Cited verbatim by the scoring layer's pass / fail evidence,
    # so the source must produce a value that survives a round
    # trip back into the trace UI.
    span_id: str
    parent_span_id: str | None
    name: str | None
    start_time: str | None
    end_time: str | None


@dataclass(frozen=True)
class ToolSpan(_SpanCommon):
    input: dict[str, Any] | None = None
    output: str | None = None


@dataclass(frozen=True)
class AgentSpan(_SpanCommon):
    routing_reason: str | None = None


@dataclass(frozen=True)
class GenerationSpan(_SpanCommon):
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    input_cost_usd: float | None = None
    output_cost_usd: float | None = None
    total_cost_usd: float | None = None


@dataclass(frozen=True)
class OtherSpan(_SpanCommon):
    pass


# A normalized span is exactly one of the four variants. Encoding
# kind as the dataclass type (rather than a SpanKind enum field)
# means impossible states are unrepresentable: a TOOL span cannot
# carry a model, a GENERATION cannot carry tool arguments, the
# transform layer can dispatch via isinstance(), and the type
# checker validates each construction site against the right field
# set.
NormalizedSpan: TypeAlias = (
    ToolSpan | AgentSpan | GenerationSpan | OtherSpan
)


__all__ = [
    "AgentSpan",
    "GenerationSpan",
    "NormalizedSpan",
    "OtherSpan",
    "ToolSpan",
]
