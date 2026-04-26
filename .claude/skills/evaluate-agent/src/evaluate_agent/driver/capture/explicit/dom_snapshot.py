"""
Record labeled DOM snapshots to the run artifact layout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from evaluate_agent.artifact_layout import RunArtifactLayout


class DOMSnapshotable(Protocol):
    async def content(self) -> str: ...


_LABEL_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


class InvalidDOMSnapshotLabel(ValueError):
    def __init__(self, label: str) -> None:
        self.label = label
        super().__init__(
            f"DOM snapshot label {label!r} is not a valid slug.\n"
            f"To proceed: pass a lowercase, letter-led label using only [a-z0-9_-] "
            f"(e.g. 'landing', 'after_submit', 'final_state'). Labels become part of the "
            f"DOM snapshot filename so they must be filesystem-safe."
        )


@dataclass
class DOMSnapshotter:
    layout: RunArtifactLayout
    case_id: str
    _step: int = field(default=0, init=False, repr=False)

    async def snapshot(
        self,
        page: DOMSnapshotable,
        label: str,
    ) -> Path:
        if not _LABEL_RE.match(label):
            raise InvalidDOMSnapshotLabel(label)
        self._step += 1
        path = self.layout.dom_snapshot_path(
            self.case_id, self._step, label
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        content = await page.content()
        path.write_text(content, encoding="utf-8")
        return path


__all__ = [
    "DOMSnapshotable",
    "DOMSnapshotter",
    "InvalidDOMSnapshotLabel",
]
