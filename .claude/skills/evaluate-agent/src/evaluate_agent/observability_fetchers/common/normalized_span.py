"""
Source-agnostic span shape that every per-source normalizer emits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SpanKind(str, Enum):
    AGENT = "AGENT"
    TOOL = "TOOL"
    GENERATION = "GENERATION"
    OTHER = "OTHER"


@dataclass(frozen=True)
class NormalizedSpan:
    # The span's stable identifier within its source backend.
    # Cited verbatim by the scoring layer's pass / fail evidence,
    # so the source must produce a value that survives a round
    # trip back into the trace UI.
    span_id: str
    parent_span_id: str | None
    name: str | None
    kind: SpanKind
    start_time: str | None
    end_time: str | None
    # TOOL-only payload. Populated only when kind == TOOL; left
    # None on every other kind so the canonical transform layer
    # can route on field presence without re-checking kind.
    input: dict[str, Any] | None = None
    output: str | None = None
    # AGENT-only payload — captured rationale for the routing
    # decision, when the source surfaces one.
    routing_reason: str | None = None
    # GENERATION-only payload — usage and cost telemetry.
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    input_cost_usd: float | None = None
    output_cost_usd: float | None = None
    total_cost_usd: float | None = None


__all__ = ["NormalizedSpan", "SpanKind"]
