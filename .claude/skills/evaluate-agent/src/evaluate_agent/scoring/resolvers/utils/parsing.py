"""
JSON parsing helpers shared across the resolvers in this package.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from evaluate_agent.common.errors.scoring import (
    ObservabilityLogMalformedError,
)
from pydantic import BaseModel, ValidationError

_Entry = TypeVar("_Entry", bound=BaseModel)


def parse_jsonl_log(
    path: Path,
    entry_model_cls: type[_Entry],
) -> tuple[_Entry, ...]:
    entries: list[_Entry] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(
            handle, start=1
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ObservabilityLogMalformedError(
                    path=path,
                    line_number=line_number,
                    parse_error=(
                        f"invalid JSON ({exc.msg})"
                    ),
                ) from exc
            try:
                entries.append(
                    entry_model_cls.model_validate(obj)
                )
            except ValidationError as exc:
                raise ObservabilityLogMalformedError(
                    path=path,
                    line_number=line_number,
                    parse_error=(
                        f"schema violation against "
                        f"{entry_model_cls.__name__}: "
                        f"{exc}"
                    ),
                ) from exc
    return tuple(entries)


def parse_single_json_log(
    path: Path,
    model_cls: type[_Entry],
) -> _Entry:
    raw = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ObservabilityLogMalformedError(
            path=path,
            line_number=None,
            parse_error=f"invalid JSON ({exc.msg})",
        ) from exc
    try:
        return model_cls.model_validate(obj)
    except ValidationError as exc:
        raise ObservabilityLogMalformedError(
            path=path,
            line_number=None,
            parse_error=(
                f"schema violation against "
                f"{model_cls.__name__}: {exc}"
            ),
        ) from exc


__all__ = [
    "parse_jsonl_log",
    "parse_single_json_log",
]
