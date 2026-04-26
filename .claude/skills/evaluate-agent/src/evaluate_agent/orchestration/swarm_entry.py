"""
Per-case entry inside a swarm plan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.schema import Slug
from pydantic import Field

from .driver_invocation import DriverInvocation


class SwarmEntry(StrictFrozen):
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


__all__ = ["SwarmEntry"]
