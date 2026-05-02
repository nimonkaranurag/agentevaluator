"""
Run-aware filesystem layout for an agent's captured artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .filenames import (
    DOM_SNAPSHOT_EXT,
    DOM_SNAPSHOTS_SUBDIR,
    EXPLICIT_DOM_PREFIX,
    OBSERVABILITY_SUBDIR,
    ROUTING_DECISION_LOG_FILENAME,
    STEP_COUNT_FILENAME,
    TOOL_CALL_LOG_FILENAME,
    TRACE_SUBDIR,
)
from .run_id import RUN_ID_FORMAT, parse_run_id


@dataclass(frozen=True)
class RunArtifactLayout:
    runs_root: Path
    agent_name: str
    run_id: str

    def __post_init__(self) -> None:
        parse_run_id(self.run_id)

    @classmethod
    def for_agent(
        cls,
        agent_name: str,
        runs_root: Path = Path("runs"),
        now: datetime | None = None,
    ) -> "RunArtifactLayout":
        clock = now or datetime.now(timezone.utc)
        return cls(
            runs_root=runs_root,
            agent_name=agent_name,
            run_id=clock.strftime(RUN_ID_FORMAT),
        )

    @classmethod
    def from_run_id(
        cls,
        agent_name: str,
        run_id: str,
        runs_root: Path = Path("runs"),
    ) -> "RunArtifactLayout":
        return cls(
            runs_root=runs_root,
            agent_name=agent_name,
            run_id=run_id,
        )

    @property
    def run_dir(self) -> Path:
        return (
            self.runs_root / self.agent_name / self.run_id
        )

    def case_dir(self, case_id: str) -> Path:
        return self.run_dir / case_id

    def screenshot_path(
        self,
        case_id: str,
        step_number: int,
        label: str,
    ) -> Path:
        filename = f"step-{step_number:03d}-{label}.png"
        return self.case_dir(case_id) / filename

    def dom_snapshot_dir(self, case_id: str) -> Path:
        return (
            self.case_dir(case_id)
            / TRACE_SUBDIR
            / DOM_SNAPSHOTS_SUBDIR
        )

    def dom_snapshot_path(
        self,
        case_id: str,
        step_number: int,
        label: str,
    ) -> Path:
        filename = (
            f"{EXPLICIT_DOM_PREFIX}-{step_number:03d}-"
            f"{label}.{DOM_SNAPSHOT_EXT}"
        )
        return self.dom_snapshot_dir(case_id) / filename

    def observability_log_dir(self, case_id: str) -> Path:
        return (
            self.case_dir(case_id)
            / TRACE_SUBDIR
            / OBSERVABILITY_SUBDIR
        )

    def tool_call_log_path(self, case_id: str) -> Path:
        return (
            self.observability_log_dir(case_id)
            / TOOL_CALL_LOG_FILENAME
        )

    def routing_decision_log_path(
        self, case_id: str
    ) -> Path:
        return (
            self.observability_log_dir(case_id)
            / ROUTING_DECISION_LOG_FILENAME
        )

    def step_count_path(self, case_id: str) -> Path:
        return (
            self.observability_log_dir(case_id)
            / STEP_COUNT_FILENAME
        )


__all__ = ["RunArtifactLayout"]
