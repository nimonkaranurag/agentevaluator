"""
Deterministic filesystem layout for run artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

RUN_ID_FORMAT = "%Y%m%dT%H%M%SZ"
TRACE_SUBDIR = "trace"
DOM_SNAPSHOTS_SUBDIR = "dom"
DOM_SNAPSHOT_EXT = "html"
EXPLICIT_DOM_PREFIX = "step"
_HAR_FILENAME = "network.har"
_REQUESTS_FILENAME = "requests.jsonl"
_RESPONSES_FILENAME = "responses.jsonl"
_CONSOLE_FILENAME = "console.jsonl"
_PAGE_ERRORS_FILENAME = "page_errors.jsonl"
_AUTO_PREFIX = "auto"


class InvalidRunId(ValueError):
    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(
            f"Run id {value!r} is not formatted as "
            f"YYYYMMDDTHHMMSSZ (UTC, e.g. "
            f"20260425T173000Z).\n"
            f"To proceed:\n"
            f"  (1) Confirm the run id was produced by "
            f"RunArtifactLayout.for_agent or copied "
            f"verbatim from a swarm plan's run_id "
            f"field.\n"
            f"  (2) If the value was supplied via "
            f"--run-id on a CLI invocation, fix the "
            f"argument or omit the flag to default to "
            f"the current UTC clock."
        )


@dataclass(frozen=True)
class TraceArtifactPaths:
    trace_dir: Path
    har_path: Path
    requests_path: Path
    responses_path: Path
    console_path: Path
    page_errors_path: Path

    def ensure_dir(self) -> None:
        self.trace_dir.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class RunArtifactLayout:
    runs_root: Path
    agent_name: str
    run_id: str

    def __post_init__(self) -> None:
        try:
            datetime.strptime(self.run_id, RUN_ID_FORMAT)
        except ValueError as exc:
            raise InvalidRunId(self.run_id) from exc

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

    def auto_screenshot_path(
        self,
        case_id: str,
        step_number: int,
        event_suffix: str,
    ) -> Path:
        filename = (
            f"{_AUTO_PREFIX}-{step_number:03d}-"
            f"{event_suffix}.png"
        )
        return self.case_dir(case_id) / filename

    def trace_paths(
        self, case_id: str
    ) -> TraceArtifactPaths:
        trace_dir = self.case_dir(case_id) / TRACE_SUBDIR
        return TraceArtifactPaths(
            trace_dir=trace_dir,
            har_path=trace_dir / _HAR_FILENAME,
            requests_path=trace_dir / _REQUESTS_FILENAME,
            responses_path=trace_dir / _RESPONSES_FILENAME,
            console_path=trace_dir / _CONSOLE_FILENAME,
            page_errors_path=trace_dir
            / _PAGE_ERRORS_FILENAME,
        )

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

    def auto_dom_snapshot_path(
        self,
        case_id: str,
        step_number: int,
        event_suffix: str,
    ) -> Path:
        filename = (
            f"{_AUTO_PREFIX}-{step_number:03d}-"
            f"{event_suffix}.{DOM_SNAPSHOT_EXT}"
        )
        return self.dom_snapshot_dir(case_id) / filename


__all__ = [
    "DOM_SNAPSHOT_EXT",
    "DOM_SNAPSHOTS_SUBDIR",
    "EXPLICIT_DOM_PREFIX",
    "RUN_ID_FORMAT",
    "TRACE_SUBDIR",
    "InvalidRunId",
    "RunArtifactLayout",
    "TraceArtifactPaths",
]
