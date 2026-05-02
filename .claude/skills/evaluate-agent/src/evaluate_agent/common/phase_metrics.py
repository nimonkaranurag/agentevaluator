"""
Per-phase timing collector and JSON metrics document for CI consumption.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal

from evaluate_agent.common.types import StrictFrozen
from pydantic import Field

ExitStatus = Literal["success", "error"]


class PhaseMetric(StrictFrozen):
    name: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Phase identifier, e.g. load_manifest, "
                "score, render. Phases are recorded in "
                "the order they completed."
            ),
        ),
    ]
    duration_ms: Annotated[
        float,
        Field(
            ge=0.0,
            description=(
                "Wall-clock duration of the phase in "
                "milliseconds, captured via "
                "time.perf_counter."
            ),
        ),
    ]


class MetricsContext(StrictFrozen):
    run_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Run identifier the script operated on, "
                "set after the value is known. None for "
                "scripts that do not bind to a run "
                "(validate_manifest, discover_manifests)."
            ),
        ),
    ]
    case_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Case identifier the script operated on, "
                "set for per-case scripts (score_case, "
                "fetch_observability)."
            ),
        ),
    ]
    manifest_path: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Absolute path to the manifest the script "
                "loaded, set after the manifest is bound."
            ),
        ),
    ]
    case_dir: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Absolute path to the case directory the "
                "script operated on, when applicable."
            ),
        ),
    ]


class ScriptMetrics(StrictFrozen):
    script: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Script identifier (matches the "
                "argparse prog name)."
            ),
        ),
    ]
    started_at: Annotated[
        str,
        Field(
            description=(
                "ISO-8601 UTC timestamp at which the "
                "metrics collector was constructed."
            ),
        ),
    ]
    ended_at: Annotated[
        str,
        Field(
            description=(
                "ISO-8601 UTC timestamp at which the "
                "metrics document was emitted."
            ),
        ),
    ]
    total_duration_ms: Annotated[
        float,
        Field(
            ge=0.0,
            description=(
                "Wall-clock duration between "
                "started_at and ended_at in "
                "milliseconds. Equals or exceeds the "
                "sum of phase durations."
            ),
        ),
    ]
    exit_status: Annotated[
        ExitStatus,
        Field(
            description=(
                "Whether the script reached its primary "
                "output (success) or aborted on an "
                "actionable error (error)."
            ),
        ),
    ]
    context: Annotated[
        MetricsContext,
        Field(
            description=(
                "Identifiers the script bound while "
                "running (run_id, case_id, "
                "manifest_path, case_dir). Fields the "
                "script never bound are null."
            ),
        ),
    ]
    phases: Annotated[
        tuple[PhaseMetric, ...],
        Field(
            description=(
                "Phase records in completion order. "
                "Empty when the script aborted before "
                "any phase started."
            ),
        ),
    ]


class MetricsCollector:
    def __init__(self, *, script_name: str) -> None:
        self._script_name = script_name
        self._started_at = datetime.now(timezone.utc)
        self._started_perf = perf_counter()
        self._phases: list[PhaseMetric] = []
        self._context_fields: dict[str, str] = {}

    def set_context(self, **fields: str | None) -> None:
        for key, value in fields.items():
            if value is None:
                self._context_fields.pop(key, None)
            else:
                self._context_fields[key] = str(value)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        started = perf_counter()
        try:
            yield
        finally:
            self._phases.append(
                PhaseMetric(
                    name=name,
                    duration_ms=(perf_counter() - started)
                    * 1000.0,
                )
            )

    def build(
        self, *, exit_status: ExitStatus
    ) -> ScriptMetrics:
        ended_at = datetime.now(timezone.utc)
        total_ms = (
            perf_counter() - self._started_perf
        ) * 1000.0
        return ScriptMetrics(
            script=self._script_name,
            started_at=self._started_at.isoformat(),
            ended_at=ended_at.isoformat(),
            total_duration_ms=total_ms,
            exit_status=exit_status,
            context=MetricsContext(**self._context_fields),
            phases=tuple(self._phases),
        )

    def emit_if_configured(
        self,
        path: Path | None,
        *,
        exit_status: ExitStatus,
    ) -> None:
        if path is None:
            return
        document = self.build(exit_status=exit_status)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            document.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )


__all__ = [
    "ExitStatus",
    "MetricsCollector",
    "MetricsContext",
    "PhaseMetric",
    "ScriptMetrics",
]
