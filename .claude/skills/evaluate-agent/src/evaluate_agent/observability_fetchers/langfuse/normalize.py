"""
Map LangFuse observation dictionaries onto the canonical NormalizedSpan shape.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from evaluate_agent.observability_fetchers.common import (
    NormalizedSpan,
    SpanKind,
    dict_or_none,
    iso_timestamp_or_none,
    mapping_or_empty,
    non_negative_float_or_none,
    non_negative_int_or_none,
    string_or_none,
)

from .observation_types import (
    LANGFUSE_AGENT_TYPE,
    LANGFUSE_GENERATION_TYPE,
    LANGFUSE_TOOL_TYPE,
)


def normalize_langfuse_observations(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[NormalizedSpan, ...]:
    return tuple(
        span
        for span in (
            _normalize_one(obs) for obs in observations
        )
        if span is not None
    )


def _normalize_one(
    observation: Mapping[str, Any],
) -> NormalizedSpan | None:
    span_id = string_or_none(observation.get("id"))
    if span_id is None:
        return None
    kind = _kind_from_type(
        string_or_none(observation.get("type"))
    )
    return NormalizedSpan(
        span_id=span_id,
        parent_span_id=string_or_none(
            observation.get("parent_observation_id")
        ),
        name=string_or_none(observation.get("name")),
        kind=kind,
        start_time=iso_timestamp_or_none(
            observation.get("start_time")
        ),
        end_time=iso_timestamp_or_none(
            observation.get("end_time")
        ),
        input=(
            dict_or_none(observation.get("input"))
            if kind is SpanKind.TOOL
            else None
        ),
        output=(
            string_or_none(observation.get("output"))
            if kind is SpanKind.TOOL
            else None
        ),
        routing_reason=(
            _routing_reason(observation)
            if kind is SpanKind.AGENT
            else None
        ),
        **_generation_fields(observation, kind),
    )


def _kind_from_type(
    observation_type: str | None,
) -> SpanKind:
    if observation_type == LANGFUSE_TOOL_TYPE:
        return SpanKind.TOOL
    if observation_type == LANGFUSE_AGENT_TYPE:
        return SpanKind.AGENT
    if observation_type == LANGFUSE_GENERATION_TYPE:
        return SpanKind.GENERATION
    return SpanKind.OTHER


def _routing_reason(
    observation: Mapping[str, Any],
) -> str | None:
    metadata = observation.get("metadata")
    if isinstance(metadata, Mapping):
        candidate = metadata.get("reason")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _generation_fields(
    observation: Mapping[str, Any],
    kind: SpanKind,
) -> dict[str, Any]:
    if kind is not SpanKind.GENERATION:
        return {}
    usage = mapping_or_empty(observation.get("usage"))
    cost = mapping_or_empty(observation.get("cost_details"))
    return {
        "model": string_or_none(observation.get("model")),
        "input_tokens": non_negative_int_or_none(
            usage.get("input")
        ),
        "output_tokens": non_negative_int_or_none(
            usage.get("output")
        ),
        "total_tokens": non_negative_int_or_none(
            usage.get("total")
        ),
        "input_cost_usd": non_negative_float_or_none(
            cost.get("input")
        ),
        "output_cost_usd": non_negative_float_or_none(
            cost.get("output")
        ),
        "total_cost_usd": non_negative_float_or_none(
            cost.get("total")
        ),
    }


__all__ = ["normalize_langfuse_observations"]
