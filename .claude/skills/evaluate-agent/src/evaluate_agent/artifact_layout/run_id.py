"""
UTC run-id format and validation for artifact directory naming.
"""

from __future__ import annotations

from datetime import datetime

RUN_ID_FORMAT = "%Y%m%dT%H%M%SZ"


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


def parse_run_id(value: str) -> None:
    try:
        datetime.strptime(value, RUN_ID_FORMAT)
    except ValueError as exc:
        raise InvalidRunId(value) from exc


__all__ = [
    "InvalidRunId",
    "RUN_ID_FORMAT",
    "parse_run_id",
]
