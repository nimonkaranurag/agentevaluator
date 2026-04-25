"""
Automatic page screenshot on every main-frame navigation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Callable,
    Protocol,
)

from ..artifact_layout import RunArtifactLayout
from .auto_dom_snapshot import NavigatedFrame
from .capture import Screenshotable
from .trace import PageEventEmitter

_NAVIGATED_EVENT = "framenavigated"
_AUTO_EVENT_SUFFIX = "nav"


class AutoScreenshotablePage(
    Screenshotable, PageEventEmitter, Protocol
):
    pass


class AutoScreenshotCollectorAlreadyAttached(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "AutoScreenshotCollector.attach was called while the collector is already attached to a page.\n"
            "To proceed, choose one:\n"
            "  (1) Call .detach(page) on the attached page, then .attach(new_page) on the replacement. The collector keeps its step counter and continues numbering automatic captures monotonically across the swap.\n"
            "  (2) Instantiate a separate AutoScreenshotCollector and attach each one to its own page exactly once.\n"
            "A single collector multiplexed across pages would interleave captures from unrelated sessions into the same case directory; the evaluator treats that as an ordering bug and rejects the trace."
        )


@dataclass
class AutoScreenshotCollector:
    layout: RunArtifactLayout
    case_id: str
    _step: int = field(default=0, init=False, repr=False)
    _pending: set[asyncio.Task[Any]] = field(
        default_factory=set, init=False, repr=False
    )
    _handler: Callable[[Any], None] | None = field(
        default=None, init=False, repr=False
    )
    _attached_page: AutoScreenshotablePage | None = field(
        default=None, init=False, repr=False
    )

    def attach(self, page: AutoScreenshotablePage) -> None:
        if self._handler is not None:
            raise AutoScreenshotCollectorAlreadyAttached()

        def on_navigated(frame: NavigatedFrame) -> None:
            if _is_subframe(frame):
                return
            self._step += 1
            step_number = self._step
            task = asyncio.ensure_future(
                self._capture(page, step_number)
            )
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)

        page.on(_NAVIGATED_EVENT, on_navigated)
        self._handler = on_navigated
        self._attached_page = page

    def detach(self, page: AutoScreenshotablePage) -> None:
        if self._handler is None:
            return
        page.remove_listener(
            _NAVIGATED_EVENT, self._handler
        )
        self._handler = None
        self._attached_page = None

    async def flush(self) -> None:
        if not self._pending:
            return
        pending = list(self._pending)
        await asyncio.gather(
            *pending, return_exceptions=True
        )

    async def _capture(
        self,
        page: Screenshotable,
        step_number: int,
    ) -> Path:
        path = self.layout.auto_screenshot_path(
            self.case_id,
            step_number,
            _AUTO_EVENT_SUFFIX,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path))
        return path


def _is_subframe(frame: NavigatedFrame) -> bool:
    return getattr(frame, "parent_frame", None) is not None


__all__ = [
    "AutoScreenshotCollector",
    "AutoScreenshotCollectorAlreadyAttached",
    "AutoScreenshotablePage",
]
