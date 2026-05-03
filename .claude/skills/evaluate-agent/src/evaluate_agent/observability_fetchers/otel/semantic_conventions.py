"""
OpenTelemetry GenAI semantic-convention attribute keys consumed by the OTEL normalizer.
"""

from __future__ import annotations

# Attribute keys defined by the upstream GenAI semantic
# conventions.
ATTR_OPERATION_NAME = "gen_ai.operation.name"
ATTR_REQUEST_MODEL = "gen_ai.request.model"
ATTR_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
ATTR_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
ATTR_USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"
# Cost attributes are not yet part of the upstream GenAI
# semconv spec; we standardise on these keys so any agent that
# wants `max_total_cost_usd` to resolve via OTEL emits them
# under a stable namespace.
ATTR_USAGE_INPUT_COST_USD = "gen_ai.usage.input_cost_usd"
ATTR_USAGE_OUTPUT_COST_USD = "gen_ai.usage.output_cost_usd"
ATTR_USAGE_TOTAL_COST_USD = "gen_ai.usage.total_cost_usd"
ATTR_TOOL_NAME = "gen_ai.tool.name"
ATTR_TOOL_PARAMETERS = "gen_ai.tool.parameters"
ATTR_TOOL_OUTPUT = "gen_ai.tool.output"
ATTR_AGENT_NAME = "gen_ai.agent.name"
# Same caveat as the cost attributes — routing.reason is not in
# the semconv spec yet but the canonical RoutingDecision schema
# carries an optional reason field, so we adopt the same key
# shape.
ATTR_ROUTING_REASON = "gen_ai.routing.reason"

OPERATION_EXECUTE_TOOL = "execute_tool"
OPERATION_INVOKE_AGENT = "invoke_agent"
OPERATION_CREATE_AGENT = "create_agent"
GENERATION_OPERATIONS = frozenset(
    {"chat", "text_completion", "embeddings"}
)
AGENT_OPERATIONS = frozenset(
    {OPERATION_INVOKE_AGENT, OPERATION_CREATE_AGENT}
)


__all__ = [
    "AGENT_OPERATIONS",
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
    "GENERATION_OPERATIONS",
    "OPERATION_CREATE_AGENT",
    "OPERATION_EXECUTE_TOOL",
    "OPERATION_INVOKE_AGENT",
]
