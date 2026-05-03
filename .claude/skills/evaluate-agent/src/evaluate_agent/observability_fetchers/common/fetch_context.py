"""
Per-invocation context object passed from per-source orchestrators into the shared assembly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FetchContext:
    # Per-source orchestrators (langfuse/fetcher.py, otel/fetcher.py)
    # build this once and hand it to assemble_fetched_observability.
    # Keeping the cross-source contract behind a single value object
    # means adding a field (metrics collector, manifest_path, etc.)
    # touches the dataclass + assembly only — never the per-source
    # call sites.
    case_dir: Path
    endpoint: str
    session_id: str
    trace_ids: tuple[str, ...]


__all__ = ["FetchContext"]
