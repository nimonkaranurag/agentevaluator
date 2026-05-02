"""
Fetch LangFuse traces for a case and persist them to the standard format.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluate_agent.common.errors.observability_fetcher import (
    LangfuseQueryFailed,
)
from evaluate_agent.manifest.schema import LangfuseSource

from .langfuse_credentials import (
    LangfuseCredentials,
    resolve_langfuse_credentials,
)
from .langfuse_transform import (
    transform_observations_to_generations,
    transform_observations_to_routing_decisions,
    transform_observations_to_step_count,
    transform_observations_to_tool_calls,
)
from .observability_writer import (
    WrittenObservabilityArtifacts,
    write_observability_artifacts,
)

_LIST_TRACES_PAGE_SIZE = 100
_FETCH_OBSERVATIONS_PAGE_SIZE = 100


@dataclass(frozen=True)
class FetchedObservability:
    host: str
    session_id: str
    trace_ids: tuple[str, ...]
    observation_count: int
    tool_call_count: int
    routing_decision_count: int
    step_count_total: int
    generation_count: int
    total_tokens: int | None
    total_cost_usd: float | None
    total_latency_ms: int | None
    written: WrittenObservabilityArtifacts


def fetch_langfuse_observability(
    *,
    case_dir: Path,
    source: LangfuseSource,
    session_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
) -> FetchedObservability:
    credentials = resolve_langfuse_credentials(source)
    client = _construct_langfuse_client(credentials)

    trace_ids = _list_trace_ids_for_session(
        client,
        session_id=session_id,
        since=since,
        until=until,
        host=credentials.host,
    )

    observations: list[Mapping[str, Any]] = []
    for trace_id in trace_ids:
        observations.extend(
            _fetch_trace_observations(
                client,
                trace_id=trace_id,
                host=credentials.host,
            )
        )

    tool_calls = transform_observations_to_tool_calls(
        observations
    )
    routing_decisions = (
        transform_observations_to_routing_decisions(
            observations
        )
    )
    step_count = transform_observations_to_step_count(
        observations
    )
    generations = transform_observations_to_generations(
        observations
    )

    written = write_observability_artifacts(
        case_dir=case_dir,
        tool_calls=tool_calls,
        routing_decisions=routing_decisions,
        step_count=step_count,
        generations=generations,
    )

    return FetchedObservability(
        host=credentials.host,
        session_id=session_id,
        trace_ids=tuple(trace_ids),
        observation_count=len(observations),
        tool_call_count=len(tool_calls),
        routing_decision_count=len(routing_decisions),
        step_count_total=step_count.total_steps,
        generation_count=len(generations),
        total_tokens=_optional_sum(
            g.total_tokens for g in generations
        ),
        total_cost_usd=_optional_sum(
            g.total_cost_usd for g in generations
        ),
        total_latency_ms=_optional_sum(
            g.latency_ms for g in generations
        ),
        written=written,
    )


def _optional_sum(values: Any) -> Any:
    collected = [v for v in values if v is not None]
    if not collected:
        return None
    if all(isinstance(v, int) for v in collected):
        return sum(collected)
    return float(sum(collected))


def _construct_langfuse_client(
    credentials: LangfuseCredentials,
) -> Any:
    try:
        from langfuse import Langfuse
    except ImportError as exc:
        raise LangfuseQueryFailed(
            host=credentials.host,
            operation="construct LangFuse client",
            detail=(
                f"the 'langfuse' package is not "
                f"importable in the active environment "
                f"({exc})"
            ),
        ) from exc

    return Langfuse(
        public_key=credentials.public_key,
        secret_key=credentials.secret_key,
        host=credentials.host,
    )


def _list_trace_ids_for_session(
    client: Any,
    *,
    session_id: str,
    since: datetime | None,
    until: datetime | None,
    host: str,
) -> list[str]:
    trace_ids: list[str] = []
    page = 1
    try:
        while True:
            response = client.api.trace.list(
                session_id=session_id,
                from_timestamp=since,
                to_timestamp=until,
                limit=_LIST_TRACES_PAGE_SIZE,
                page=page,
            )
            page_traces = list(response.data)
            for trace in page_traces:
                trace_id = getattr(trace, "id", None)
                if isinstance(trace_id, str) and trace_id:
                    trace_ids.append(trace_id)
            if len(page_traces) < _LIST_TRACES_PAGE_SIZE:
                return trace_ids
            page += 1
    except LangfuseQueryFailed:
        raise
    except Exception as exc:
        raise LangfuseQueryFailed(
            host=host,
            operation=(
                f"list traces for session "
                f"{session_id!r}"
            ),
            detail=str(exc),
        ) from exc


def _fetch_trace_observations(
    client: Any,
    *,
    trace_id: str,
    host: str,
) -> list[Mapping[str, Any]]:
    observations: list[Mapping[str, Any]] = []
    page = 1
    try:
        while True:
            response = client.api.observations.get_many(
                trace_id=trace_id,
                limit=_FETCH_OBSERVATIONS_PAGE_SIZE,
                page=page,
            )
            page_observations = list(response.data)
            for observation in page_observations:
                observations.append(
                    _observation_to_dict(observation)
                )
            if (
                len(page_observations)
                < _FETCH_OBSERVATIONS_PAGE_SIZE
            ):
                return observations
            page += 1
    except LangfuseQueryFailed:
        raise
    except Exception as exc:
        raise LangfuseQueryFailed(
            host=host,
            operation=(
                f"fetch observations for trace "
                f"{trace_id!r}"
            ),
            detail=str(exc),
        ) from exc


def _observation_to_dict(
    observation: Any,
) -> Mapping[str, Any]:
    if hasattr(observation, "model_dump"):
        return observation.model_dump(mode="python")
    if isinstance(observation, Mapping):
        return observation
    return {
        attr: getattr(observation, attr, None)
        for attr in (
            "id",
            "name",
            "type",
            "parent_observation_id",
            "metadata",
            "input",
            "output",
            "start_time",
            "end_time",
            "trace_id",
            "model",
            "usage",
            "cost_details",
        )
    }


__all__ = [
    "FetchedObservability",
    "fetch_langfuse_observability",
]
