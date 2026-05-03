"""
Map LangFuse observation dictionaries onto the canonical NormalizedSpan variants.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from evaluate_agent.observability_fetchers.common import (
    AgentSpan,
    GenerationSpan,
    NormalizedSpan,
    OtherSpan,
    ToolSpan,
    dict_or_none,
    iso_timestamp_or_none,
    mapping_or_empty,
    non_negative_float_or_none,
    non_negative_int_or_none,
    string_or_none,
)

# Discriminator values LangFuse stamps on its `Observation.type`
# field. Tests import these to construct synthetic observations
# against the same vocabulary the fetcher consumes.
LANGFUSE_TOOL_TYPE = "TOOL"
LANGFUSE_AGENT_TYPE = "AGENT"
LANGFUSE_GENERATION_TYPE = "GENERATION"


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
    common = {
        "span_id": span_id,
        "parent_span_id": string_or_none(
            observation.get("parent_observation_id")
        ),
        "name": string_or_none(observation.get("name")),
        "start_time": iso_timestamp_or_none(
            observation.get("start_time")
        ),
        "end_time": iso_timestamp_or_none(
            observation.get("end_time")
        ),
    }
    observation_type = string_or_none(
        observation.get("type")
    )
    if observation_type == LANGFUSE_TOOL_TYPE:
        return ToolSpan(
            **common,
            input=dict_or_none(observation.get("input")),
            output=string_or_none(
                observation.get("output")
            ),
        )
    if observation_type == LANGFUSE_AGENT_TYPE:
        return AgentSpan(
            **common,
            routing_reason=_routing_reason(observation),
        )
    if observation_type == LANGFUSE_GENERATION_TYPE:
        usage = mapping_or_empty(observation.get("usage"))
        cost = mapping_or_empty(
            observation.get("cost_details")
        )
        return GenerationSpan(
            **common,
            model=string_or_none(observation.get("model")),
            input_tokens=non_negative_int_or_none(
                usage.get("input")
            ),
            output_tokens=non_negative_int_or_none(
                usage.get("output")
            ),
            total_tokens=non_negative_int_or_none(
                usage.get("total")
            ),
            input_cost_usd=non_negative_float_or_none(
                cost.get("input")
            ),
            output_cost_usd=non_negative_float_or_none(
                cost.get("output")
            ),
            total_cost_usd=non_negative_float_or_none(
                cost.get("total")
            ),
        )
    return OtherSpan(**common)


def _routing_reason(
    observation: Mapping[str, Any],
) -> str | None:
    metadata = observation.get("metadata")
    if isinstance(metadata, Mapping):
        candidate = metadata.get("reason")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


__all__ = [
    "LANGFUSE_AGENT_TYPE",
    "LANGFUSE_GENERATION_TYPE",
    "LANGFUSE_TOOL_TYPE",
    "normalize_langfuse_observations",
]
