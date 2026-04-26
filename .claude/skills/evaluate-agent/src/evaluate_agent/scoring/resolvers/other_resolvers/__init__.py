"""
Resolvers for non-log artifact types (single JSON document, DOM snapshot).
"""

from .dom_snapshot import (
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
    "ResolvedDOMSnapshot",
    "ResolvedStepCount",
    "extract_visible_text",
    "post_submit_dom_snapshot_dir",
    "resolve_post_submit_dom_snapshot",
    "resolve_step_count",
    "step_count_path",
]
