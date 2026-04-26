"""
Automatic page screenshot on every uncaught page error.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .collector_base import (
    EventTriggeredCaptureCollector,
    EventTriggeredCapturePage,
)
from .page_error_dom_snapshot import (
    PAGE_ERROR_EVENT,
    PAGE_ERROR_EVENT_SUFFIX,
)


class PageErrorScreenshotCollectorAlreadyAttached(
    RuntimeError
):
    def __init__(self) -> None:
        super().__init__(
            "PageErrorScreenshotCollector.attach was called while the collector is already attached to a page.\n"
            "To proceed, choose one:\n"
            "  (1) Call .detach(page) on the attached page, then .attach(new_page) on the replacement. The collector keeps its step counter and continues numbering automatic captures monotonically across the swap.\n"
            "  (2) Instantiate a separate PageErrorScreenshotCollector and attach each one to its own page exactly once.\n"
            "A single collector multiplexed across pages would interleave captures from unrelated sessions into the same case directory; the evaluator treats that as an ordering bug and rejects the trace."
        )


@dataclass
class PageErrorScreenshotCollector(
    EventTriggeredCaptureCollector
):
    @property
    def event_name(self) -> str:
        return PAGE_ERROR_EVENT

    def _event_should_be_captured(
        self, payload: Any
    ) -> bool:
        return True

    async def _capture(
        self,
        page: EventTriggeredCapturePage,
        step_number: int,
    ) -> Path:
        path = self.layout.auto_screenshot_path(
            self.case_id,
            step_number,
            PAGE_ERROR_EVENT_SUFFIX,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path))
        return path

    def _raise_already_attached(self) -> None:
        raise PageErrorScreenshotCollectorAlreadyAttached()


__all__ = [
    "PageErrorScreenshotCollector",
    "PageErrorScreenshotCollectorAlreadyAttached",
]
