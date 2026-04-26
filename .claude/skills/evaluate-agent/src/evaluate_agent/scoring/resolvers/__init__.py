"""
Locate captured artifacts on disk and return their parsed shapes.

The resolvers package is split into three concerns:

- `dom_snapshot` — DOM HTML resolution + visible-text extraction
  (single-artifact resolver, no structured-log parsing).
- `observability/` — structured-log resolvers for the observability
  domain (tool calls, routing decisions, step count).
- `baseline_trace/` — structured-log resolvers for the always-on
  baseline-trace domain (uncaught page errors).

Callers import the public surface from this composition module.
"""

from .baseline_trace import (
    ResolvedPageErrorsLog,
    page_errors_log_path,
    resolve_page_errors_log,
)
from .dom_snapshot import (
    ResolvedDOMSnapshot,
    extract_visible_text,
    post_submit_dom_snapshot_dir,
    resolve_post_submit_dom_snapshot,
)
from .observability import (
    ResolvedRoutingDecisionLog,
    ResolvedStepCount,
    ResolvedToolCallLog,
    resolve_routing_decision_log,
    resolve_step_count,
    resolve_tool_call_log,
    routing_decision_log_path,
    step_count_path,
    tool_call_log_path,
)

__all__ = [
    "ResolvedDOMSnapshot",
    "ResolvedPageErrorsLog",
    "ResolvedRoutingDecisionLog",
    "ResolvedStepCount",
    "ResolvedToolCallLog",
    "extract_visible_text",
    "page_errors_log_path",
    "post_submit_dom_snapshot_dir",
    "resolve_page_errors_log",
    "resolve_post_submit_dom_snapshot",
    "resolve_routing_decision_log",
    "resolve_step_count",
    "resolve_tool_call_log",
    "routing_decision_log_path",
    "step_count_path",
    "tool_call_log_path",
]
