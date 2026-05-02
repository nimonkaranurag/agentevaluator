"""
Resolvers for non-log artifact types (single JSON document, DOM snapshot).
"""

from .dom_snapshot import (
    DOM_SNAPSHOT_SIZE_CAP_BYTES,
    OversizedDOMSnapshot,
    ResolvedDOMSnapshot,
    extract_visible_text,
    post_submit_dom_snapshot_dir,
    resolve_post_submit_dom_snapshot,
)
from .step_count import (
    ResolvedStepCount,
    resolve_step_count,
    step_count_path,
)

__all__ = [
    "DOM_SNAPSHOT_SIZE_CAP_BYTES",
    "OversizedDOMSnapshot",
    "ResolvedDOMSnapshot",
    "ResolvedStepCount",
    "extract_visible_text",
    "post_submit_dom_snapshot_dir",
    "resolve_post_submit_dom_snapshot",
    "resolve_step_count",
    "step_count_path",
]
