"""
Pure transforms from LangFuse observations to the on-disk observability schema.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from evaluate_agent.scoring.observability.schema import (
    Generation,
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
    # A reasoning step is one AGENT or TOOL span that the
    # agent dispatched directly — i.e. whose parent is either
    # the trace root or another AGENT span. This excludes
    # nested TOOL-under-TOOL retries and intermediate
    # GENERATIONs (which are LLM calls inside a step, not
    # steps themselves), matching how operators count steps
    # when reading a LangFuse trace tree.
    agent_observation_ids: set[str] = {
        observation_id
        for observation_id in (
            _string_or_none(obs.get("id"))
            for obs in _observations_of_type(
                observations, LANGFUSE_AGENT_TYPE
            )
        )
        if observation_id is not None
    }
    step_observations = sorted(
        (
            obs
            for obs in observations
            if _string_or_none(obs.get("type"))
            in (
                LANGFUSE_AGENT_TYPE,
                LANGFUSE_TOOL_TYPE,
            )
            and _string_or_none(obs.get("id")) is not None
            and _step_parent_is_agent_or_root(
                obs.get("parent_observation_id"),
                agent_observation_ids=agent_observation_ids,
            )
        ),
        key=lambda obs: _start_time_sort_key(
            obs.get("start_time")
        ),
    )
    span_ids = tuple(
        _string_or_none(obs.get("id"))  # type: ignore[misc]
        for obs in step_observations
    )
    return StepCount(
        total_steps=len(span_ids),
        step_span_ids=span_ids,
    )


def _step_parent_is_agent_or_root(
    parent_observation_id: Any,
    *,
    agent_observation_ids: set[str],
) -> bool:
    parent_id = _string_or_none(parent_observation_id)
    if parent_id is None:
        return True
    return parent_id in agent_observation_ids


def transform_observations_to_generations(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[Generation, ...]:
    entries: list[Generation] = []
    for observation in _observations_of_type(
        observations, LANGFUSE_GENERATION_TYPE
    ):
        span_id = _string_or_none(observation.get("id"))
        if span_id is None:
            continue
        usage = _mapping_or_empty(observation.get("usage"))
        cost = _mapping_or_empty(
            observation.get("cost_details")
        )
        entries.append(
            Generation(
                span_id=span_id,
                model=_string_or_none(
                    observation.get("model")
                ),
                input_tokens=_non_negative_int_or_none(
                    usage.get("input")
                ),
                output_tokens=_non_negative_int_or_none(
                    usage.get("output")
                ),
                total_tokens=_non_negative_int_or_none(
                    usage.get("total")
                ),
                input_cost_usd=_non_negative_float_or_none(
                    cost.get("input")
                ),
                output_cost_usd=_non_negative_float_or_none(
                    cost.get("output")
                ),
                total_cost_usd=_non_negative_float_or_none(
                    cost.get("total")
                ),
                started_at=_iso_timestamp_or_none(
                    observation.get("start_time")
                ),
                ended_at=_iso_timestamp_or_none(
                    observation.get("end_time")
                ),
            )
        )
    return tuple(entries)


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


def _mapping_or_empty(
    value: Any,
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _non_negative_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value >= 0:
        return int(value)
    return None


def _non_negative_float_or_none(
    value: Any,
) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


__all__ = [
    "LANGFUSE_AGENT_TYPE",
    "LANGFUSE_GENERATION_TYPE",
    "LANGFUSE_TOOL_TYPE",
    "transform_observations_to_generations",
    "transform_observations_to_routing_decisions",
    "transform_observations_to_step_count",
    "transform_observations_to_tool_calls",
]
