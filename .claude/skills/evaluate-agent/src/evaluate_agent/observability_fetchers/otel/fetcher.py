"""
Orchestrate the OTEL fetch: credentials, OTLP queries, normalize, hand off to the shared assembly.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluate_agent.manifest.schema import OtelSource
from evaluate_agent.observability_fetchers.common import (
    FetchContext,
    assemble_fetched_observability,
)
from evaluate_agent.observability_fetchers.fetcher import (
    FetchedObservability,
)

from .client import (
    fetch_trace_resource_spans,
    list_trace_ids_for_session,
)
from .credentials import resolve_otel_credentials
from .normalize import normalize_otel_resource_spans


def fetch_otel_observability(
    *,
    case_dir: Path,
    source: OtelSource,
    session_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
) -> FetchedObservability:
    credentials = resolve_otel_credentials(source)

    trace_ids = list_trace_ids_for_session(
        credentials,
        session_id=session_id,
        since=since,
        until=until,
    )

    resource_spans: list[Mapping[str, Any]] = []
    for trace_id in trace_ids:
        resource_spans.extend(
            fetch_trace_resource_spans(
                credentials,
                trace_id=trace_id,
            )
        )

    spans = normalize_otel_resource_spans(resource_spans)
    return assemble_fetched_observability(
        spans,
        context=FetchContext(
            case_dir=case_dir,
            endpoint=credentials.endpoint,
            session_id=session_id,
            trace_ids=tuple(trace_ids),
        ),
    )


__all__ = ["fetch_otel_observability"]
