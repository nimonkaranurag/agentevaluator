"""
Filename constants the driver writes and the scoring layer reads.
"""

from __future__ import annotations

TRACE_SUBDIR = "trace"
DOM_SNAPSHOTS_SUBDIR = "dom"
DOM_SNAPSHOT_EXT = "html"
EXPLICIT_DOM_PREFIX = "step"
OBSERVABILITY_SUBDIR = "observability"
TOOL_CALL_LOG_FILENAME = "tool_calls.jsonl"
ROUTING_DECISION_LOG_FILENAME = "routing_decisions.jsonl"
STEP_COUNT_FILENAME = "step_count.json"
PAGE_ERRORS_LOG_FILENAME = "page_errors.jsonl"
HAR_FILENAME = "network.har"
REQUESTS_FILENAME = "requests.jsonl"
RESPONSES_FILENAME = "responses.jsonl"
CONSOLE_FILENAME = "console.jsonl"
AUTO_PREFIX = "auto"


__all__ = [
    "AUTO_PREFIX",
    "CONSOLE_FILENAME",
    "DOM_SNAPSHOTS_SUBDIR",
    "DOM_SNAPSHOT_EXT",
    "EXPLICIT_DOM_PREFIX",
    "HAR_FILENAME",
    "OBSERVABILITY_SUBDIR",
    "PAGE_ERRORS_LOG_FILENAME",
    "REQUESTS_FILENAME",
    "RESPONSES_FILENAME",
    "ROUTING_DECISION_LOG_FILENAME",
    "STEP_COUNT_FILENAME",
    "TOOL_CALL_LOG_FILENAME",
    "TRACE_SUBDIR",
]
