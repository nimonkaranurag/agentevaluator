"""
SwarmPlan record + plan_swarm composer for MCP-driven case fan-out.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated

from evaluate_agent.artifact_layout import (
    LANDING_LABEL,
    POST_SUBMIT_LABEL,
    RunArtifactLayout,
    parse_run_id,
)
from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.schema import (
    AgentManifest,
    Slug,
)
from pydantic import AfterValidator, Field

from .case_directive import CaseDirective

_LANDING_STEP_NUMBER = 1
_POST_SUBMIT_STEP_NUMBER = 2


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
                "YYYYMMDDTHHMMSSZ (UTC). Every directive "
                "in this plan writes artifacts under "
                "<runs_root>/<agent_name>/<run_id>/."
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
    directives: Annotated[
        tuple[CaseDirective, ...],
        Field(
            min_length=1,
            description=(
                "One CaseDirective per case declared in "
                "the manifest, in declaration order. "
                "Each directive is self-contained and "
                "MUST be dispatched to its own Claude "
                "sub-agent so every case runs in its own "
                "isolated MCP browser context."
            ),
        ),
    ]


def plan_swarm(
    manifest: AgentManifest,
    manifest_path: Path,
    *,
    runs_root: Path = Path("runs"),
    now: datetime | None = None,
) -> SwarmPlan:
    layout = RunArtifactLayout.for_agent(
        agent_name=manifest.name,
        runs_root=runs_root.resolve(),
        now=now,
    )
    resolved_manifest = manifest_path.resolve()
    directives = tuple(
        CaseDirective(
            case_id=case.id,
            case_dir=layout.case_dir(case.id),
            url=manifest.access.url,
            case_input=case.input,
            input_selector=manifest.interaction.input_selector,
            preconditions=tuple(
                manifest.interaction.preconditions
            ),
            response_wait_ms=manifest.interaction.response_wait_ms,
            landing_screenshot_path=layout.screenshot_path(
                case.id,
                _LANDING_STEP_NUMBER,
                LANDING_LABEL,
            ),
            landing_dom_snapshot_path=layout.dom_snapshot_path(
                case.id,
                _LANDING_STEP_NUMBER,
                LANDING_LABEL,
            ),
            after_submit_screenshot_path=layout.screenshot_path(
                case.id,
                _POST_SUBMIT_STEP_NUMBER,
                POST_SUBMIT_LABEL,
            ),
            after_submit_dom_snapshot_path=layout.dom_snapshot_path(
                case.id,
                _POST_SUBMIT_STEP_NUMBER,
                POST_SUBMIT_LABEL,
            ),
            ui_introspection=manifest.observability.ui_introspection,
            tool_call_log_path=layout.tool_call_log_path(
                case.id
            ),
            routing_decision_log_path=layout.routing_decision_log_path(
                case.id
            ),
            step_count_path=layout.step_count_path(case.id),
            generation_log_path=layout.generation_log_path(
                case.id
            ),
        )
        for case in manifest.cases
    )
    return SwarmPlan(
        run_id=layout.run_id,
        agent_name=manifest.name,
        runs_root=layout.runs_root,
        manifest_path=resolved_manifest,
        directives=directives,
    )


__all__ = ["SwarmPlan", "plan_swarm"]
