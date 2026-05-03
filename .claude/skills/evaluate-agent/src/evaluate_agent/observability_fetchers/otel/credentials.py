"""
Resolve OTEL endpoint and OTLP-shaped headers from the manifest's declared env var.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from evaluate_agent.common.errors.observability_fetchers import (
    OtelHeadersEnvMissing,
    OtelHeadersMalformed,
)
from evaluate_agent.manifest.schema import OtelSource


@dataclass(frozen=True)
class OtelCredentials:
    endpoint: str
    headers: Mapping[str, str] = field(default_factory=dict)


def resolve_otel_credentials(
    source: OtelSource,
) -> OtelCredentials:
    headers: Mapping[str, str] = {}
    if source.headers_env is not None:
        headers = _parse_otlp_headers(
            env_var=source.headers_env,
            raw=_require_env(env_var=source.headers_env),
        )
    return OtelCredentials(
        endpoint=str(source.endpoint).rstrip("/"),
        headers=headers,
    )


def _require_env(*, env_var: str) -> str:
    value = os.environ.get(env_var)
    if not value:
        raise OtelHeadersEnvMissing(env_var)
    return value


def _parse_otlp_headers(
    *,
    env_var: str,
    raw: str,
) -> dict[str, str]:
    # OTLP exporter convention (OTEL_EXPORTER_OTLP_HEADERS):
    # comma-separated key=value pairs, no spaces around the
    # delimiters. We accept surrounding whitespace defensively
    # but reject any pair that lacks the `=` separator so a
    # malformed value never silently turns into an empty header.
    headers: dict[str, str] = {}
    for chunk in raw.split(","):
        pair = chunk.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise OtelHeadersMalformed(
                env_var=env_var,
                offending_pair=pair,
            )
        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise OtelHeadersMalformed(
                env_var=env_var,
                offending_pair=pair,
            )
        headers[key] = value
    return headers


__all__ = [
    "OtelCredentials",
    "resolve_otel_credentials",
]
