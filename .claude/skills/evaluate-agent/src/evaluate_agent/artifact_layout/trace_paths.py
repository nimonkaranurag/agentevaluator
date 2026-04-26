"""
Trace artifact path bundle written by the driver's TraceCollector.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TraceArtifactPaths:
    trace_dir: Path
    har_path: Path
    requests_path: Path
    responses_path: Path
    console_path: Path
    page_errors_path: Path

    def ensure_dir(self) -> None:
        self.trace_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["TraceArtifactPaths"]
