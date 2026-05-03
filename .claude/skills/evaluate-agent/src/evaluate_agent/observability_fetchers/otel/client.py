"""
OTLP query boundary: HTTP GET against a Tempo-style search and trace API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from evaluate_agent.common.errors.observability_fetchers import (
    OtelQueryFailed,
)

from .credentials import OtelCredentials

_HTTP_TIMEOUT_SECONDS = 30.0


def list_trace_ids_for_session(
    credentials: OtelCredentials,
    *,
    session_id: str,
    since: datetime | None,
    until: datetime | None,
) -> list[str]:
    params: dict[str, str] = {
        # Tempo's TraceQL-lite tag-based search expects the
        # `tags` query string in the canonical key=value form.
        # We pin to `session.id` because that's the attribute
        # the manifest agreement asks emitters to stamp every
        # case with — same contract that LangFuse's session_id
        # filter relies on.
        "tags": f"session.id={session_id}",
    }
    if since is not None:
        params["start"] = str(int(since.timestamp()))
    if until is not None:
        params["end"] = str(int(until.timestamp()))

    url = (
        f"{credentials.endpoint}/api/search"
        f"?{urlencode(params)}"
    )
    payload = _http_get_json(
        url,
        credentials,
        operation=(
            f"search traces for session {session_id!r}"
        ),
    )

    trace_ids: list[str] = []
    for trace in payload.get("traces") or []:
        if not isinstance(trace, Mapping):
            continue
        # Tempo capitalises the field as `traceID`, but the
        # OTLP/JSON spec uses `traceId`. Accept both so the
        # client survives a backend that emits either casing.
        candidate = trace.get("traceID") or trace.get(
            "traceId"
        )
        if isinstance(candidate, str) and candidate:
            trace_ids.append(candidate)
    return trace_ids


def fetch_trace_resource_spans(
    credentials: OtelCredentials,
    *,
    trace_id: str,
) -> list[Mapping[str, Any]]:
    url = f"{credentials.endpoint}/api/traces/{trace_id}"
    payload = _http_get_json(
        url,
        credentials,
        operation=f"fetch trace {trace_id!r}",
    )
    # Tempo returns `batches`; pure OTLP/JSON returns
    # `resourceSpans`. Both shapes carry the same scopeSpans /
    # spans structure, so the normalize layer doesn't care
    # which key got used at the wire.
    batches = payload.get("batches")
    if isinstance(batches, list):
        return [
            batch
            for batch in batches
            if isinstance(batch, Mapping)
        ]
    resource_spans = payload.get("resourceSpans")
    if isinstance(resource_spans, list):
        return [
            entry
            for entry in resource_spans
            if isinstance(entry, Mapping)
        ]
    return []


def _http_get_json(
    url: str,
    credentials: OtelCredentials,
    *,
    operation: str,
) -> Mapping[str, Any]:
    headers = {"Accept": "application/json"}
    headers.update(credentials.headers)
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(
            request, timeout=_HTTP_TIMEOUT_SECONDS
        ) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise OtelQueryFailed(
            endpoint=credentials.endpoint,
            operation=operation,
            detail=f"HTTP {exc.code}: {exc.reason}",
        ) from exc
    except urllib.error.URLError as exc:
        raise OtelQueryFailed(
            endpoint=credentials.endpoint,
            operation=operation,
            detail=f"URLError: {exc.reason}",
        ) from exc
    except OSError as exc:
        raise OtelQueryFailed(
            endpoint=credentials.endpoint,
            operation=operation,
            detail=f"OSError: {exc}",
        ) from exc

    try:
        decoded = json.loads(body.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise OtelQueryFailed(
            endpoint=credentials.endpoint,
            operation=operation,
            detail=(f"response body is not JSON ({exc})"),
        ) from exc

    if not isinstance(decoded, Mapping):
        raise OtelQueryFailed(
            endpoint=credentials.endpoint,
            operation=operation,
            detail=(
                "response body is JSON but not an object"
            ),
        )
    return decoded


__all__ = [
    "fetch_trace_resource_spans",
    "list_trace_ids_for_session",
]
