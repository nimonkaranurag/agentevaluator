"""
Cross-source primitives shared by every observability-fetcher implementation.
"""

from .assembly import assemble_fetched_observability
from .coerce import (
    dict_or_none,
    iso_timestamp_or_none,
    mapping_or_empty,
    non_negative_float_or_none,
    non_negative_int_or_none,
    string_or_none,
)
from .fetch_context import FetchContext
from .normalized_span import (
    AgentSpan,
    GenerationSpan,
    NormalizedSpan,
    OtherSpan,
    ToolSpan,
)
from .stats import (
    GenerationStats,
    aggregate_generation_stats,
)

__all__ = [
    "AgentSpan",
    "FetchContext",
    "GenerationSpan",
    "GenerationStats",
    "NormalizedSpan",
    "OtherSpan",
    "ToolSpan",
    "aggregate_generation_stats",
    "assemble_fetched_observability",
    "dict_or_none",
    "iso_timestamp_or_none",
    "mapping_or_empty",
    "non_negative_float_or_none",
    "non_negative_int_or_none",
    "string_or_none",
]
