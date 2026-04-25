"""
Expand a validated manifest into a deterministic per-case fan-out plan.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
)

from ..artifact_layout import (
    RUN_ID_FORMAT,
    RunArtifactLayout,
)
from ..manifest.schema import AgentManifest, Slug

_DEFAULT_DRIVER_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "open_agent.py"
)


def _validate_run_id_format(value: str) -> str:
    try:
        datetime.strptime(value, RUN_ID_FORMAT)
    except ValueError as exc:
        raise ValueError(
            f"run_id {value!r} is not formatted as "
            f"YYYYMMDDTHHMMSSZ (UTC, e.g. "
            f"20260425T173000Z)"
        ) from exc
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DriverInvocation(_Strict):
    script: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the driver script "
                "that executes one case end-to-end. "
                "The orchestrator dispatches a sub-agent "
                "per entry and the sub-agent invokes "
                "this script with the supplied arguments."
            ),
        ),
    ]
    arguments: Annotated[
        tuple[str, ...],
        Field(
            min_length=1,
            description=(
                "Argv passed to the driver script. The "
                "first element is the absolute manifest "
                "path; the remaining elements select the "
                "case, set --submit, and pin --runs-root "
                "and --run-id so every sibling sub-agent "
                "writes artifacts into the same run "
                "directory."
            ),
        ),
    ]


class SwarmEntry(_Strict):
    case_id: Annotated[
        Slug,
        Field(
            description=(
                "Case identifier copied from "
                "manifest.cases[].id. Mirrors the case "
                "the driver_invocation selects via "
                "--case."
            ),
        ),
    ]
    case_dir: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the directory at "
                "<runs_root>/<agent_name>/<run_id>/"
                "<case_id> where the case's screenshots, "
                "DOM snapshots, and trace artifacts are "
                "written."
            ),
        ),
    ]
    driver_invocation: Annotated[
        DriverInvocation,
        Field(
            description=(
                "Self-contained invocation contract for "
                "the sub-agent that drives this case. "
                "The orchestrator hands the contract to "
                "one Claude sub-agent per entry — no "
                "shared state with siblings."
            ),
        ),
    ]


class SwarmPlan(_Strict):
    run_id: Annotated[
        str,
        AfterValidator(_validate_run_id_format),
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


__all__ = [
    "DriverInvocation",
    "SwarmEntry",
    "SwarmPlan",
    "plan_swarm",
]
