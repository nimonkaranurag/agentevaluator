"""
Locate and parse the captured routing-decision observability log for a case.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evaluate_agent.artifact_layout import (
    OBSERVABILITY_SUBDIR,
    ROUTING_DECISION_LOG_FILENAME,
    TRACE_SUBDIR,
)
from evaluate_agent.scoring.observability.schema import (
    RoutingDecision,
)
from evaluate_agent.scoring.resolvers.utils import (
    parse_jsonl_log,
)


def routing_decision_log_path(case_dir: Path) -> Path:
    return (
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / ROUTING_DECISION_LOG_FILENAME
    )


@dataclass(frozen=True)
class ResolvedRoutingDecisionLog:
    path: Path
    entries: tuple[RoutingDecision, ...]


def resolve_routing_decision_log(
    case_dir: Path,
) -> ResolvedRoutingDecisionLog | None:
    path = routing_decision_log_path(case_dir)
    if not path.is_file():
        return None
    entries = parse_jsonl_log(path, RoutingDecision)
    return ResolvedRoutingDecisionLog(
        path=path, entries=entries
    )


__all__ = [
    "ResolvedRoutingDecisionLog",
    "resolve_routing_decision_log",
    "routing_decision_log_path",
]
