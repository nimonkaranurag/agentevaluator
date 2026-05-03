"""
Per-invocation context — the parameters that drove the fetch, decoupled from what the backend returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FetchContext:
    # Invocation parameters: chosen by the script / caller before
    # the backend is contacted. Backend output (trace_ids, spans)
    # is passed alongside this context, not folded into it — the
    # two have different lifecycles and different change cadences.
    case_dir: Path
    endpoint: str
    session_id: str


__all__ = ["FetchContext"]
