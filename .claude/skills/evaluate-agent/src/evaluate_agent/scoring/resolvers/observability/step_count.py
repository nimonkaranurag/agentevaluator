"""
Locate and parse the captured step-count observability record for a case.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evaluate_agent.artifact_layout import (
    OBSERVABILITY_SUBDIR,
    STEP_COUNT_FILENAME,
    TRACE_SUBDIR,
)
from evaluate_agent.scoring.observability.schema import (
    StepCount,
)
from evaluate_agent.scoring.structured_log_parsing import (
    parse_single_json_log,
)


def step_count_path(case_dir: Path) -> Path:
    return (
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / STEP_COUNT_FILENAME
    )


@dataclass(frozen=True)
class ResolvedStepCount:
    path: Path
    record: StepCount


def resolve_step_count(
    case_dir: Path,
) -> ResolvedStepCount | None:
    path = step_count_path(case_dir)
    if not path.is_file():
        return None
    record = parse_single_json_log(path, StepCount)
    return ResolvedStepCount(path=path, record=record)


__all__ = [
    "ResolvedStepCount",
    "resolve_step_count",
    "step_count_path",
]
