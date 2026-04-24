"""
Deterministic filesystem layout for run artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .trace import TraceArtifactPaths

_RUN_ID_FORMAT = "%Y%m%dT%H%M%SZ"
_TRACE_SUBDIR = "trace"
_HAR_FILENAME = "network.har"
_REQUESTS_FILENAME = "requests.jsonl"
_RESPONSES_FILENAME = "responses.jsonl"
_CONSOLE_FILENAME = "console.jsonl"
_PAGE_ERRORS_FILENAME = "page_errors.jsonl"


@dataclass(frozen=True)
class RunArtifactLayout:
    runs_root: Path
    agent_name: str
    run_id: str

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
            run_id=clock.strftime(_RUN_ID_FORMAT),
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

    def trace_paths(
        self, case_id: str
    ) -> TraceArtifactPaths:
        trace_dir = self.case_dir(case_id) / _TRACE_SUBDIR
        return TraceArtifactPaths(
            trace_dir=trace_dir,
            har_path=trace_dir / _HAR_FILENAME,
            requests_path=trace_dir / _REQUESTS_FILENAME,
            responses_path=trace_dir / _RESPONSES_FILENAME,
            console_path=trace_dir / _CONSOLE_FILENAME,
            page_errors_path=trace_dir
            / _PAGE_ERRORS_FILENAME,
        )


__all__ = ["RunArtifactLayout"]
