"""
Self-contained driver invocation handed to one sub-agent per swarm entry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from evaluate_agent.common.types import StrictFrozen
from pydantic import Field


class DriverInvocation(StrictFrozen):
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


__all__ = ["DriverInvocation"]
