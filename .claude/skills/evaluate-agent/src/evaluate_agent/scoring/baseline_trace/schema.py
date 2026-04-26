"""
On-disk schemas for the baseline-trace log files the evaluators consume.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageErrorEntry(_Strict):
    ts: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "UTC ISO-8601 timestamp, recorded at the "
                "moment the page event fired. Cited "
                "verbatim by passed and failed outcomes "
                "so a reader can locate the entry inside "
                "the JSONL stream by time."
            ),
        ),
    ]
    message: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Stringified uncaught-error payload "
                "(`str(error)` from the Playwright "
                "pageerror event). Cited verbatim by "
                "failed outcomes so a reader sees the "
                "exact message the agent UI threw."
            ),
        ),
    ]


__all__ = ["PageErrorEntry"]
