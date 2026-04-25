"""
Locate the post-submit DOM snapshot for a captured case.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..artifact_layout import (
    DOM_SNAPSHOT_EXT,
    DOM_SNAPSHOTS_SUBDIR,
    EXPLICIT_DOM_PREFIX,
    TRACE_SUBDIR,
)
from ..capture_labels import POST_SUBMIT_LABEL


def post_submit_dom_snapshot_dir(
    case_dir: Path,
) -> Path:
    return case_dir / TRACE_SUBDIR / DOM_SNAPSHOTS_SUBDIR


_FILENAME_PATTERN = re.compile(
    rf"^{re.escape(EXPLICIT_DOM_PREFIX)}-(\d+)-"
    rf"{re.escape(POST_SUBMIT_LABEL)}\."
    rf"{re.escape(DOM_SNAPSHOT_EXT)}$"
)


def resolve_post_submit_dom_snapshot(
    case_dir: Path,
) -> Path | None:
    dom_dir = post_submit_dom_snapshot_dir(case_dir)
    if not dom_dir.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for child in dom_dir.iterdir():
        match = _FILENAME_PATTERN.match(child.name)
        if match:
            candidates.append((int(match.group(1)), child))
    if not candidates:
        return None
    return max(candidates, key=lambda pair: pair[0])[1]


__all__ = [
    "post_submit_dom_snapshot_dir",
    "resolve_post_submit_dom_snapshot",
]
