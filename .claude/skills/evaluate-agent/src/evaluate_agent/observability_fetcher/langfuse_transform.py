"""
Pure transforms from LangFuse observations to the on-disk observability schema.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from evaluate_agent.scoring.observability.schema import (
    RoutingDecision,
    StepCount,
    ToolCall,
)

LANGFUSE_TOOL_TYPE = "TOOL"
LANGFUSE_AGENT_TYPE = "AGENT"
LANGFUSE_GENERATION_TYPE = "GENERATION"


def transform_observations_to_tool_calls(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[ToolCall, ...]:
    entries: list[ToolCall] = []
    for observation in _observations_of_type(
        observations, LANGFUSE_TOOL_TYPE
    ):
        tool_name = _string_or_none(observation.get("name"))
        span_id = _string_or_none(observation.get("id"))
        if tool_name is None or span_id is None:
            continue
        entries.append(
            ToolCall(
                tool_name=tool_name,
                span_id=span_id,
                arguments=_dict_or_none(
                    observation.get("input")
                ),
                result=_string_or_none(
                    observation.get("output")
                ),
                timestamp=_iso_timestamp_or_none(
                    observation.get("start_time")
                ),
            )
        )
    return tuple(entries)


def transform_observations_to_routing_decisions(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[RoutingDecision, ...]:
    parent_agent_name_by_id = {
        _string_or_none(obs.get("id")): _string_or_none(
            obs.get("name")
        )
        for obs in observations
        if _string_or_none(obs.get("type"))
        == LANGFUSE_AGENT_TYPE
    }
    entries: list[RoutingDecision] = []
    for observation in _observations_of_type(
        observations, LANGFUSE_AGENT_TYPE
    ):
        target_agent = _string_or_none(
            observation.get("name")
        )
        span_id = _string_or_none(observation.get("id"))
        if target_agent is None or span_id is None:
            continue
        parent_id = _string_or_none(
            observation.get("parent_observation_id")
        )
        entries.append(
            RoutingDecision(
                target_agent=target_agent,
                span_id=span_id,
                from_agent=parent_agent_name_by_id.get(
                    parent_id
                ),
                reason=_routing_reason(observation),
                timestamp=_iso_timestamp_or_none(
                    observation.get("start_time")
                ),
            )
        )
    return tuple(entries)


def transform_observations_to_step_count(
    observations: Sequence[Mapping[str, Any]],
) -> StepCount:
    generations = sorted(
        (
            obs
            for obs in _observations_of_type(
                observations, LANGFUSE_GENERATION_TYPE
            )
            if _string_or_none(obs.get("id")) is not None
        ),
        key=lambda obs: _start_time_sort_key(
            obs.get("start_time")
        ),
    )
    span_ids = tuple(
        _string_or_none(obs.get("id"))  # type: ignore[misc]
        for obs in generations
    )
    return StepCount(
        total_steps=len(span_ids),
        step_span_ids=span_ids,
    )


def _observations_of_type(
    observations: Sequence[Mapping[str, Any]],
    expected_type: str,
) -> list[Mapping[str, Any]]:
    return [
        obs
        for obs in observations
        if _string_or_none(obs.get("type")) == expected_type
    ]


def _routing_reason(
    observation: Mapping[str, Any],
) -> str | None:
    metadata = observation.get("metadata")
    if isinstance(metadata, Mapping):
        candidate = metadata.get("reason")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def _dict_or_none(
    value: Any,
) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    return None


def _iso_timestamp_or_none(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _start_time_sort_key(value: Any) -> tuple[int, str]:
    if isinstance(value, datetime):
        return (0, value.isoformat())
    if isinstance(value, str) and value:
        return (0, value)
    return (1, "")


__all__ = [
    "LANGFUSE_AGENT_TYPE",
    "LANGFUSE_GENERATION_TYPE",
    "LANGFUSE_TOOL_TYPE",
    "transform_observations_to_routing_decisions",
    "transform_observations_to_step_count",
    "transform_observations_to_tool_calls",
]
