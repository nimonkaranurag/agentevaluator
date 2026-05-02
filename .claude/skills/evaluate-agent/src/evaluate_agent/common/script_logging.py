"""
Script-level logging configuration and structured-record formatters.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Literal

LogFormat = Literal["text", "json"]

LOG_FORMATS: tuple[LogFormat, ...] = ("text", "json")

CONTEXT_FIELD_NAMES: tuple[str, ...] = (
    "run_id",
    "case_id",
    "assertion_kind",
    "manifest_path",
    "case_dir",
)


class TextLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        prefix = f"[{record.levelname}] " f"{record.name}: "
        message = record.getMessage()
        context = _extract_context_fields(record)
        if context:
            context_str = " ".join(
                f"{k}={v}" for k, v in context.items()
            )
            message = f"{message} ({context_str})"
        if record.exc_info:
            message = (
                f"{message}\n"
                f"{self.formatException(record.exc_info)}"
            )
        return prefix + message


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_extract_context_fields(record))
        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )
        return json.dumps(payload, default=str)


def _extract_context_fields(
    record: logging.LogRecord,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for name in CONTEXT_FIELD_NAMES:
        value = getattr(record, name, None)
        if value is not None:
            fields[name] = (
                str(value)
                if not isinstance(
                    value, (str, int, float, bool)
                )
                else value
            )
    return fields


def configure_script_logging(
    *,
    script_name: str,
    log_format: LogFormat,
    level: int = logging.INFO,
) -> logging.Logger:
    if log_format not in LOG_FORMATS:
        raise ValueError(
            f"log_format must be one of {LOG_FORMATS}, "
            f"got {log_format!r}"
        )
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        JsonLogFormatter()
        if log_format == "json"
        else TextLogFormatter()
    )
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
    return logging.getLogger(script_name)


__all__ = [
    "CONTEXT_FIELD_NAMES",
    "JsonLogFormatter",
    "LOG_FORMATS",
    "LogFormat",
    "TextLogFormatter",
    "configure_script_logging",
]
