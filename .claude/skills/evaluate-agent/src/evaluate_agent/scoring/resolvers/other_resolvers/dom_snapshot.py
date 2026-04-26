"""
Locate the post-submit DOM snapshot for a captured case and extract its
user-visible text in a single resolution step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from evaluate_agent.artifact_layout import (
    DOM_SNAPSHOT_EXT,
    DOM_SNAPSHOTS_SUBDIR,
    EXPLICIT_DOM_PREFIX,
    POST_SUBMIT_LABEL,
    TRACE_SUBDIR,
)

_NON_VISIBLE_TAGS = (
    "script",
    "style",
    "noscript",
    "template",
)
_WHITESPACE_RUN = re.compile(r"\s+")


def post_submit_dom_snapshot_dir(
    case_dir: Path,
) -> Path:
    return case_dir / TRACE_SUBDIR / DOM_SNAPSHOTS_SUBDIR


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_NON_VISIBLE_TAGS):
        tag.decompose()
    for comment in soup.find_all(
        string=lambda node: isinstance(node, Comment)
    ):
        comment.extract()
    text = soup.get_text(separator=" ", strip=True)
    return _WHITESPACE_RUN.sub(" ", text).strip()


@dataclass(frozen=True)
class ResolvedDOMSnapshot:
    path: Path
    visible_text: str


_FILENAME_PATTERN = re.compile(
    rf"^{re.escape(EXPLICIT_DOM_PREFIX)}-(\d+)-"
    rf"{re.escape(POST_SUBMIT_LABEL)}\."
    rf"{re.escape(DOM_SNAPSHOT_EXT)}$"
)


def resolve_post_submit_dom_snapshot(
    case_dir: Path,
) -> ResolvedDOMSnapshot | None:
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
    latest = max(candidates, key=lambda pair: pair[0])[1]
    return ResolvedDOMSnapshot(
        path=latest,
        visible_text=extract_visible_text(
            latest.read_text(encoding="utf-8")
        ),
    )


__all__ = [
    "ResolvedDOMSnapshot",
    "extract_visible_text",
    "post_submit_dom_snapshot_dir",
    "resolve_post_submit_dom_snapshot",
]
