"""
Automatic DOM snapshot on every main-frame navigation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .base import (
    EventTriggeredCaptureCollector,
    EventTriggeredCapturePage,
)

NAVIGATED_EVENT = "framenavigated"
NAVIGATED_EVENT_SUFFIX = "nav"


class NavigatedFrame(Protocol):
    parent_frame: Any


class AutoDOMSnapshotCollectorAlreadyAttached(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "AutoDOMSnapshotCollector.attach was called while the collector is already attached to a page.\n"
            "To proceed, choose one:\n"
            "  (1) Call .detach(page) on the attached page, then .attach(new_page) on the replacement. The collector keeps its step counter and continues numbering automatic captures monotonically across the swap.\n"
            "  (2) Instantiate a separate AutoDOMSnapshotCollector and attach each one to its own page exactly once.\n"
            "A single collector multiplexed across pages would interleave captures from unrelated sessions into the same DOM directory; the evaluator treats that as an ordering bug and rejects the trace."
        )


@dataclass
class AutoDOMSnapshotCollector(
    EventTriggeredCaptureCollector
):
    @property
    def event_name(self) -> str:
        return NAVIGATED_EVENT

    def _event_should_be_captured(
        self, payload: NavigatedFrame
    ) -> bool:
        return (
            getattr(payload, "parent_frame", None) is None
        )

    async def _capture(
        self,
        page: EventTriggeredCapturePage,
        step_number: int,
    ) -> Path:
        path = self.layout.auto_dom_snapshot_path(
            self.case_id,
            step_number,
            NAVIGATED_EVENT_SUFFIX,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        content = await page.content()
        path.write_text(content, encoding="utf-8")
        return path

    def _raise_already_attached(self) -> None:
        raise AutoDOMSnapshotCollectorAlreadyAttached()


__all__ = [
    "AutoDOMSnapshotCollector",
    "AutoDOMSnapshotCollectorAlreadyAttached",
    "NAVIGATED_EVENT",
    "NAVIGATED_EVENT_SUFFIX",
    "NavigatedFrame",
]
