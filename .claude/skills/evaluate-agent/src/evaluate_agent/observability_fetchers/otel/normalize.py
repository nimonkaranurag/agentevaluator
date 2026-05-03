"""
Map OTLP resourceSpans onto the canonical NormalizedSpan variants.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from evaluate_agent.observability_fetchers.common import (
    AgentSpan,
    GenerationSpan,
    NormalizedSpan,
    OtherSpan,
    ToolSpan,
    non_negative_float_or_none,
    non_negative_int_or_none,
    string_or_none,
)

from .semantic_conventions import (
    AGENT_OPERATIONS,
    ATTR_AGENT_NAME,
    ATTR_OPERATION_NAME,
    ATTR_REQUEST_MODEL,
    ATTR_ROUTING_REASON,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_PARAMETERS,
    ATTR_USAGE_INPUT_COST_USD,
    ATTR_USAGE_INPUT_TOKENS,
    ATTR_USAGE_OUTPUT_COST_USD,
    ATTR_USAGE_OUTPUT_TOKENS,
    ATTR_USAGE_TOTAL_COST_USD,
    ATTR_USAGE_TOTAL_TOKENS,
    GENERATION_OPERATIONS,
    OPERATION_EXECUTE_TOOL,
)


def normalize_otel_resource_spans(
    resource_spans: Sequence[Mapping[str, Any]],
) -> tuple[NormalizedSpan, ...]:
    return tuple(
        span
        for span in (
            _normalize_one(raw_span)
            for raw_span in _walk_spans(resource_spans)
        )
        if span is not None
    )


def _walk_spans(
    resource_spans: Sequence[Mapping[str, Any]],
) -> Sequence[Mapping[str, Any]]:
    out: list[Mapping[str, Any]] = []
    for batch in resource_spans:
        if not isinstance(batch, Mapping):
            continue
        for scope_block in batch.get("scopeSpans") or []:
            if not isinstance(scope_block, Mapping):
                continue
            for raw_span in scope_block.get("spans") or []:
                if isinstance(raw_span, Mapping):
                    out.append(raw_span)
    return out


def _normalize_one(
    raw: Mapping[str, Any],
) -> NormalizedSpan | None:
    span_id = string_or_none(raw.get("spanId"))
    if span_id is None:
        return None
    attributes = _flatten_attributes(raw.get("attributes"))
    common = {
        "span_id": span_id,
        "parent_span_id": string_or_none(
            raw.get("parentSpanId")
        ),
        "name": _span_name_default(raw),
        "start_time": _unix_nano_to_iso(
            raw.get("startTimeUnixNano")
        ),
        "end_time": _unix_nano_to_iso(
            raw.get("endTimeUnixNano")
        ),
    }
    operation = attributes.get(ATTR_OPERATION_NAME)
    if (
        operation == OPERATION_EXECUTE_TOOL
        or ATTR_TOOL_NAME in attributes
    ):
        return ToolSpan(
            **{
                **common,
                "name": (
                    string_or_none(
                        attributes.get(ATTR_TOOL_NAME)
                    )
                    or common["name"]
                ),
            },
            input=_tool_arguments(attributes),
            output=string_or_none(
                attributes.get(ATTR_TOOL_OUTPUT)
            ),
        )
    if (
        operation in AGENT_OPERATIONS
        or ATTR_AGENT_NAME in attributes
    ):
        return AgentSpan(
            **{
                **common,
                "name": (
                    string_or_none(
                        attributes.get(ATTR_AGENT_NAME)
                    )
                    or common["name"]
                ),
            },
            routing_reason=string_or_none(
                attributes.get(ATTR_ROUTING_REASON)
            ),
        )
    if (
        operation in GENERATION_OPERATIONS
        or ATTR_USAGE_INPUT_TOKENS in attributes
        or ATTR_USAGE_OUTPUT_TOKENS in attributes
    ):
        return GenerationSpan(
            **common,
            model=string_or_none(
                attributes.get(ATTR_REQUEST_MODEL)
            ),
            input_tokens=non_negative_int_or_none(
                attributes.get(ATTR_USAGE_INPUT_TOKENS)
            ),
            output_tokens=non_negative_int_or_none(
                attributes.get(ATTR_USAGE_OUTPUT_TOKENS)
            ),
            total_tokens=_total_tokens(attributes),
            input_cost_usd=non_negative_float_or_none(
                attributes.get(ATTR_USAGE_INPUT_COST_USD)
            ),
            output_cost_usd=non_negative_float_or_none(
                attributes.get(ATTR_USAGE_OUTPUT_COST_USD)
            ),
            total_cost_usd=non_negative_float_or_none(
                attributes.get(ATTR_USAGE_TOTAL_COST_USD)
            ),
        )
    return OtherSpan(**common)


def _span_name_default(
    raw: Mapping[str, Any],
) -> str | None:
    return string_or_none(raw.get("name"))


def _flatten_attributes(raw: Any) -> dict[str, Any]:
    # OTLP encodes attributes as a list of {key, value} where
    # `value` is a typed wrapper ({"stringValue": ...} etc.).
    # Flattening here means downstream code reads attributes as
    # an ordinary dict keyed by the semantic-convention name. A
    # malformed value (e.g. {"intValue": "abc"}) collapses to
    # None for that attribute rather than raising — the bias is
    # toward partial-data tolerance, since one bad attribute
    # should not abort an otherwise-usable case.
    if not isinstance(raw, list):
        return {}
    flattened: dict[str, Any] = {}
    for entry in raw:
        if not isinstance(entry, Mapping):
            continue
        key = string_or_none(entry.get("key"))
        if key is None:
            continue
        flattened[key] = _attribute_value(
            entry.get("value")
        )
    return flattened


def _attribute_value(raw: Any) -> Any:
    if not isinstance(raw, Mapping):
        return None
    if "stringValue" in raw:
        candidate = raw["stringValue"]
        return (
            candidate
            if isinstance(candidate, str)
            else None
        )
    if "intValue" in raw:
        # OTLP transports int64 as a string to preserve precision
        # in JSON; accept both shapes.
        try:
            return int(raw["intValue"])
        except (TypeError, ValueError):
            return None
    if "doubleValue" in raw:
        try:
            return float(raw["doubleValue"])
        except (TypeError, ValueError):
            return None
    if "boolValue" in raw:
        candidate = raw["boolValue"]
        return (
            candidate
            if isinstance(candidate, bool)
            else None
        )
    return None


def _tool_arguments(
    attributes: Mapping[str, Any],
) -> dict[str, Any] | None:
    raw = attributes.get(ATTR_TOOL_PARAMETERS)
    if isinstance(raw, str) and raw:
        # Emitters frequently serialise arguments as a JSON
        # string because OTLP attribute values can't carry
        # nested objects directly.
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, Mapping):
            return dict(parsed)
        return None
    if isinstance(raw, Mapping):
        return dict(raw)
    return None


def _total_tokens(
    attributes: Mapping[str, Any],
) -> int | None:
    explicit = non_negative_int_or_none(
        attributes.get(ATTR_USAGE_TOTAL_TOKENS)
    )
    if explicit is not None:
        return explicit
    # GenAI semconv defines input + output tokens but leaves
    # total optional. Derive it when both halves are present so
    # `max_total_tokens` can resolve against agents that only
    # emit the per-direction counts.
    inp = non_negative_int_or_none(
        attributes.get(ATTR_USAGE_INPUT_TOKENS)
    )
    out = non_negative_int_or_none(
        attributes.get(ATTR_USAGE_OUTPUT_TOKENS)
    )
    if inp is not None and out is not None:
        return inp + out
    return None


def _unix_nano_to_iso(raw: Any) -> str | None:
    if raw is None:
        return None
    try:
        nanos = int(raw)
    except (TypeError, ValueError):
        return None
    if nanos <= 0:
        return None
    return datetime.fromtimestamp(
        nanos / 1_000_000_000, tz=timezone.utc
    ).isoformat()


__all__ = ["normalize_otel_resource_spans"]
