"""
Persist canonical observability records to the standard on-disk layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evaluate_agent.artifact_layout import (
    GENERATION_LOG_FILENAME,
    OBSERVABILITY_SUBDIR,
    ROUTING_DECISION_LOG_FILENAME,
    STEP_COUNT_FILENAME,
    TOOL_CALL_LOG_FILENAME,
    TRACE_SUBDIR,
    create_owner_only_dir,
)
from evaluate_agent.scoring.observability.schema import (
    Generation,
    RoutingDecision,
    StepCount,
    ToolCall,
)


@dataclass(frozen=True)
class WrittenObservabilityArtifacts:
    tool_calls_path: Path
    routing_decisions_path: Path
    step_count_path: Path
    generations_path: Path


def observability_log_dir_for(case_dir: Path) -> Path:
    return case_dir / TRACE_SUBDIR / OBSERVABILITY_SUBDIR


def write_observability_artifacts(
    *,
    case_dir: Path,
    tool_calls: tuple[ToolCall, ...],
    routing_decisions: tuple[RoutingDecision, ...],
    step_count: StepCount,
    generations: tuple[Generation, ...],
) -> WrittenObservabilityArtifacts:
    log_dir = observability_log_dir_for(case_dir)
    create_owner_only_dir(case_dir.parent)
    create_owner_only_dir(case_dir)
    create_owner_only_dir(log_dir)

    tool_calls_path = log_dir / TOOL_CALL_LOG_FILENAME
    routing_decisions_path = (
        log_dir / ROUTING_DECISION_LOG_FILENAME
    )
    step_count_path = log_dir / STEP_COUNT_FILENAME
    generations_path = log_dir / GENERATION_LOG_FILENAME

    _write_jsonl(tool_calls_path, tool_calls)
    _write_jsonl(routing_decisions_path, routing_decisions)
    _write_jsonl(generations_path, generations)
    step_count_path.write_text(
        step_count.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return WrittenObservabilityArtifacts(
        tool_calls_path=tool_calls_path,
        routing_decisions_path=routing_decisions_path,
        step_count_path=step_count_path,
        generations_path=generations_path,
    )


def _write_jsonl(
    path: Path,
    entries: tuple[
        ToolCall | RoutingDecision | Generation, ...
    ],
) -> None:
    body = "\n".join(
        entry.model_dump_json() for entry in entries
    ) + ("\n" if entries else "")
    path.write_text(body, encoding="utf-8")


__all__ = [
    "WrittenObservabilityArtifacts",
    "observability_log_dir_for",
    "write_observability_artifacts",
]
