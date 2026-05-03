"""
Defensive coercions from untyped JSON-shaped values into canonical Python types.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def dict_or_none(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    return None


def iso_timestamp_or_none(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def mapping_or_empty(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def non_negative_int_or_none(value: Any) -> int | None:
    # bool is an int subclass in Python; reject it so True/False
    # never sneak into a token-count field as 1/0.
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value >= 0:
        return int(value)
    return None


def non_negative_float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


__all__ = [
    "dict_or_none",
    "iso_timestamp_or_none",
    "mapping_or_empty",
    "non_negative_float_or_none",
    "non_negative_int_or_none",
    "string_or_none",
]
