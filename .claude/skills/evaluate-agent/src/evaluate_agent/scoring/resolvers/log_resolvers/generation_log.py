"""
Locate and parse the captured per-generation observability log for a case.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evaluate_agent.artifact_layout import (
    GENERATION_LOG_FILENAME,
    OBSERVABILITY_SUBDIR,
    TRACE_SUBDIR,
)
from evaluate_agent.scoring.observability.schema import (
    Generation,
)
from evaluate_agent.scoring.resolvers.utils import (
    parse_jsonl_log,
)


def generation_log_path(case_dir: Path) -> Path:
    return (
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / GENERATION_LOG_FILENAME
    )


@dataclass(frozen=True)
class ResolvedGenerationLog:
    path: Path
    entries: tuple[Generation, ...]


def resolve_generation_log(
    case_dir: Path,
) -> ResolvedGenerationLog | None:
    path = generation_log_path(case_dir)
    if not path.is_file():
        return None
    entries = parse_jsonl_log(path, Generation)
    return ResolvedGenerationLog(path=path, entries=entries)


__all__ = [
    "ResolvedGenerationLog",
    "generation_log_path",
    "resolve_generation_log",
]
