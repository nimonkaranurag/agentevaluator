"""
Locate and parse the captured page-errors baseline-trace log for a case.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evaluate_agent.artifact_layout import (
    PAGE_ERRORS_LOG_FILENAME,
    TRACE_SUBDIR,
)
from evaluate_agent.scoring.baseline_trace.schema import (
    PageErrorEntry,
)
from evaluate_agent.scoring.structured_log_parsing import (
    parse_jsonl_log,
)


def page_errors_log_path(case_dir: Path) -> Path:
    return (
        case_dir / TRACE_SUBDIR / PAGE_ERRORS_LOG_FILENAME
    )


@dataclass(frozen=True)
class ResolvedPageErrorsLog:
    path: Path
    entries: tuple[PageErrorEntry, ...]


def resolve_page_errors_log(
    case_dir: Path,
) -> ResolvedPageErrorsLog | None:
    path = page_errors_log_path(case_dir)
    if not path.is_file():
        return None
    entries = parse_jsonl_log(path, PageErrorEntry)
    return ResolvedPageErrorsLog(path=path, entries=entries)


__all__ = [
    "ResolvedPageErrorsLog",
    "page_errors_log_path",
    "resolve_page_errors_log",
]
