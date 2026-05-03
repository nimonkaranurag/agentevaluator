"""
OTEL-specific fetcher: credentials, OTLP query boundary, span normalization, orchestrator.
"""

from .credentials import (
    OtelCredentials,
    resolve_otel_credentials,
)
from .fetcher import fetch_otel_observability
from .normalize import normalize_otel_resource_spans
from .semantic_conventions import (
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
    OPERATION_CREATE_AGENT,
    OPERATION_EXECUTE_TOOL,
    OPERATION_INVOKE_AGENT,
    classify_otel_span,
)

__all__ = [
    "ATTR_AGENT_NAME",
    "ATTR_OPERATION_NAME",
    "ATTR_REQUEST_MODEL",
    "ATTR_ROUTING_REASON",
    "ATTR_TOOL_NAME",
    "ATTR_TOOL_OUTPUT",
    "ATTR_TOOL_PARAMETERS",
    "ATTR_USAGE_INPUT_COST_USD",
    "ATTR_USAGE_INPUT_TOKENS",
    "ATTR_USAGE_OUTPUT_COST_USD",
    "ATTR_USAGE_OUTPUT_TOKENS",
    "ATTR_USAGE_TOTAL_COST_USD",
    "ATTR_USAGE_TOTAL_TOKENS",
    "OPERATION_CREATE_AGENT",
    "OPERATION_EXECUTE_TOOL",
    "OPERATION_INVOKE_AGENT",
    "OtelCredentials",
    "classify_otel_span",
    "fetch_otel_observability",
    "normalize_otel_resource_spans",
    "resolve_otel_credentials",
]
