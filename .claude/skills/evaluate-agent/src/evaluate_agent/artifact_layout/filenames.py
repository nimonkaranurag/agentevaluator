"""
Filename constants the orchestrator writes and the scoring layer reads.
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


__all__ = [
    "DOM_SNAPSHOTS_SUBDIR",
    "DOM_SNAPSHOT_EXT",
    "EXPLICIT_DOM_PREFIX",
    "OBSERVABILITY_SUBDIR",
    "ROUTING_DECISION_LOG_FILENAME",
    "STEP_COUNT_FILENAME",
    "TOOL_CALL_LOG_FILENAME",
    "TRACE_SUBDIR",
]
