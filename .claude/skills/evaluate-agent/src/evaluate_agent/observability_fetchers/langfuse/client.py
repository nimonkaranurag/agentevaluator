"""
LangFuse SDK boundary: client construction, paged queries, and SDK-to-dict normalisation.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any, Callable

from evaluate_agent.common.errors.observability_fetchers import (
    LangfuseQueryFailed,
)

from .credentials import LangfuseCredentials

_LIST_TRACES_PAGE_SIZE = 100
_FETCH_OBSERVATIONS_PAGE_SIZE = 100

# The fields we read from a LangFuse observation. Centralised here
# so the SDK-shape contract lives next to the SDK boundary instead
# of being implicit in the transforms.
_OBSERVATION_FIELDS = (
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


def construct_langfuse_client(
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


def list_trace_ids_for_session(
    client: Any,
    *,
    session_id: str,
    since: datetime | None,
    until: datetime | None,
    host: str,
) -> list[str]:
    operation = f"list traces for session {session_id!r}"

    def _fetch_page(page: int) -> list[Any]:
        response = client.api.trace.list(
            session_id=session_id,
            from_timestamp=since,
            to_timestamp=until,
            limit=_LIST_TRACES_PAGE_SIZE,
            page=page,
        )
        return list(response.data)

    trace_ids: list[str] = []
    for trace in _paginate(
        _fetch_page,
        page_size=_LIST_TRACES_PAGE_SIZE,
        host=host,
        operation=operation,
    ):
        trace_id = getattr(trace, "id", None)
        if isinstance(trace_id, str) and trace_id:
            trace_ids.append(trace_id)
    return trace_ids


def fetch_trace_observations(
    client: Any,
    *,
    trace_id: str,
    host: str,
) -> list[Mapping[str, Any]]:
    operation = f"fetch observations for trace {trace_id!r}"

    def _fetch_page(page: int) -> list[Any]:
        response = client.api.observations.get_many(
            trace_id=trace_id,
            limit=_FETCH_OBSERVATIONS_PAGE_SIZE,
            page=page,
        )
        return list(response.data)

    return [
        _observation_to_dict(obs)
        for obs in _paginate(
            _fetch_page,
            page_size=_FETCH_OBSERVATIONS_PAGE_SIZE,
            host=host,
            operation=operation,
        )
    ]


def _paginate(
    fetch_page: Callable[[int], list[Any]],
    *,
    page_size: int,
    host: str,
    operation: str,
) -> Iterator[Any]:
    # LangFuse's paged endpoints terminate when a page returns
    # fewer than page_size items. Centralising the loop here keeps
    # the per-endpoint call sites declarative and ensures every
    # query funnels through the same LangfuseQueryFailed wrapping.
    page = 1
    while True:
        try:
            items = fetch_page(page)
        except LangfuseQueryFailed:
            raise
        except Exception as exc:
            raise LangfuseQueryFailed(
                host=host,
                operation=operation,
                detail=str(exc),
            ) from exc
        yield from items
        if len(items) < page_size:
            return
        page += 1


def _observation_to_dict(
    observation: Any,
) -> Mapping[str, Any]:
    if hasattr(observation, "model_dump"):
        return observation.model_dump(mode="python")
    if isinstance(observation, Mapping):
        return observation
    return {
        attr: getattr(observation, attr, None)
        for attr in _OBSERVATION_FIELDS
    }


__all__ = [
    "construct_langfuse_client",
    "fetch_trace_observations",
    "list_trace_ids_for_session",
]
