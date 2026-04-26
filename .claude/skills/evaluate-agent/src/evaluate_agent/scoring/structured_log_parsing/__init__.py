"""
Generic JSONL / single-JSON log parsing primitives shared across domains.
"""

from .errors import StructuredLogParseError
from .parsing import (
    parse_jsonl_log,
    parse_single_json_log,
)

__all__ = [
    "StructuredLogParseError",
    "parse_jsonl_log",
    "parse_single_json_log",
]
