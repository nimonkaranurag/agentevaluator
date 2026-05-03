"""
Orchestrate the LangFuse fetch: credentials, paged queries, normalize, hand off to the shared assembly.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluate_agent.manifest.schema import LangfuseSource
from evaluate_agent.observability_fetchers.common import (
    FetchContext,
    assemble_fetched_observability,
)
from evaluate_agent.observability_fetchers.fetcher import (
    FetchedObservability,
)

from .client import (
    construct_langfuse_client,
    fetch_trace_observations,
    list_trace_ids_for_session,
)
from .credentials import resolve_langfuse_credentials
from .normalize import normalize_langfuse_observations


def fetch_langfuse_observability(
    *,
    case_dir: Path,
    source: LangfuseSource,
    session_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
) -> FetchedObservability:
    credentials = resolve_langfuse_credentials(source)
    client = construct_langfuse_client(credentials)

    trace_ids = list_trace_ids_for_session(
        client,
        session_id=session_id,
        since=since,
        until=until,
        host=credentials.host,
    )

    observations: list[Mapping[str, Any]] = []
    for trace_id in trace_ids:
        observations.extend(
            fetch_trace_observations(
                client,
                trace_id=trace_id,
                host=credentials.host,
            )
        )

    spans = normalize_langfuse_observations(observations)
    return assemble_fetched_observability(
        spans,
        context=FetchContext(
            case_dir=case_dir,
            endpoint=credentials.host,
            session_id=session_id,
        ),
        trace_ids=trace_ids,
    )


__all__ = ["fetch_langfuse_observability"]
