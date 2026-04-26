"""
SwarmPlan record + plan_swarm composer.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated

from evaluate_agent.artifact_layout import (
    RunArtifactLayout,
    parse_run_id,
)
from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.schema import (
    AgentManifest,
    Slug,
)
from pydantic import AfterValidator, Field

from .driver_invocation import DriverInvocation
from .swarm_entry import SwarmEntry

_DEFAULT_DRIVER_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "open_agent.py"
)


def _run_id_validator(value: str) -> str:
    parse_run_id(value)
    return value


class SwarmPlan(StrictFrozen):
    run_id: Annotated[
        str,
        AfterValidator(_run_id_validator),
        Field(
            description=(
                "Shared run timestamp committed at plan "
                "generation time. Format: "
                "YYYYMMDDTHHMMSSZ (UTC). Every entry's "
                "driver invocation reuses this id so all "
                "swarm artifacts land in a single run "
                "directory."
            ),
        ),
    ]
    agent_name: Annotated[
        Slug,
        Field(
            description=(
                "Agent identifier copied from "
                "manifest.name. Becomes part of the run "
                "directory path."
            ),
        ),
    ]
    runs_root: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the directory where "
                "run artifacts are written."
            ),
        ),
    ]
    manifest_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the validated "
                "agent.yaml the plan was generated from."
            ),
        ),
    ]
    entries: Annotated[
        tuple[SwarmEntry, ...],
        Field(
            min_length=1,
            description=(
                "One entry per case declared in the "
                "manifest, in declaration order. Each "
                "entry is self-contained — a sub-agent "
                "executes its case using only the "
                "entry's driver_invocation."
            ),
        ),
    ]


def plan_swarm(
    manifest: AgentManifest,
    manifest_path: Path,
    *,
    runs_root: Path = Path("runs"),
    driver_script: Path = _DEFAULT_DRIVER_SCRIPT,
    now: datetime | None = None,
) -> SwarmPlan:
    layout = RunArtifactLayout.for_agent(
        agent_name=manifest.name,
        runs_root=runs_root.resolve(),
        now=now,
    )
    resolved_manifest = manifest_path.resolve()
    resolved_driver = driver_script.resolve()
    entries = tuple(
        SwarmEntry(
            case_id=case.id,
            case_dir=layout.case_dir(case.id),
            driver_invocation=DriverInvocation(
                script=resolved_driver,
                arguments=(
                    str(resolved_manifest),
                    "--case",
                    case.id,
                    "--submit",
                    "--runs-root",
                    str(layout.runs_root),
                    "--run-id",
                    layout.run_id,
                ),
            ),
        )
        for case in manifest.cases
    )
    return SwarmPlan(
        run_id=layout.run_id,
        agent_name=manifest.name,
        runs_root=layout.runs_root,
        manifest_path=resolved_manifest,
        entries=entries,
    )


__all__ = ["SwarmPlan", "plan_swarm"]
