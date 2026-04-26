"""
Locate and parse the captured tool-call observability log for a case.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evaluate_agent.artifact_layout import (
    OBSERVABILITY_SUBDIR,
    TOOL_CALL_LOG_FILENAME,
    TRACE_SUBDIR,
)
from evaluate_agent.scoring.observability.schema import (
    ToolCall,
)
from evaluate_agent.scoring.structured_log_parsing import (
    parse_jsonl_log,
)


def tool_call_log_path(case_dir: Path) -> Path:
    return (
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / TOOL_CALL_LOG_FILENAME
    )


@dataclass(frozen=True)
class ResolvedToolCallLog:
    path: Path
    entries: tuple[ToolCall, ...]


def resolve_tool_call_log(
    case_dir: Path,
) -> ResolvedToolCallLog | None:
    path = tool_call_log_path(case_dir)
    if not path.is_file():
        return None
    entries = parse_jsonl_log(path, ToolCall)
    return ResolvedToolCallLog(path=path, entries=entries)


__all__ = [
    "ResolvedToolCallLog",
    "resolve_tool_call_log",
    "tool_call_log_path",
]
