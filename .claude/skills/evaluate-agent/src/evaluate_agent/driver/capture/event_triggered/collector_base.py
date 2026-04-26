"""
Template-method base for collectors that capture evidence on a page event.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from evaluate_agent.artifact_layout import RunArtifactLayout
from evaluate_agent.driver.capture.explicit import (
    DOMSnapshotable,
    Screenshotable,
)
from evaluate_agent.driver.trace import PageEventEmitter


class EventTriggeredCapturePage(
    DOMSnapshotable,
    Screenshotable,
    PageEventEmitter,
    Protocol,
):
    pass


@dataclass
class EventTriggeredCaptureCollector(ABC):
    layout: RunArtifactLayout
    case_id: str
    _step: int = field(default=0, init=False, repr=False)
    _pending: set[asyncio.Task[Any]] = field(
        default_factory=set, init=False, repr=False
    )
    _handler: Callable[[Any], None] | None = field(
        default=None, init=False, repr=False
    )

    @property
    @abstractmethod
    def event_name(self) -> str: ...

    def _event_should_be_captured(
        self, payload: Any
    ) -> bool:
        return True

    @abstractmethod
    async def _capture(
        self,
        page: EventTriggeredCapturePage,
        step_number: int,
    ) -> Path: ...

    @abstractmethod
    def _raise_already_attached(self) -> None: ...

    def attach(
        self, page: EventTriggeredCapturePage
    ) -> None:
        if self._handler is not None:
            self._raise_already_attached()

        captured_page = page

        def handler(payload: Any) -> None:
            if not self._event_should_be_captured(payload):
                return
            self._step += 1
            step_number = self._step
            task = asyncio.ensure_future(
                self._capture(captured_page, step_number)
            )
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)

        page.on(self.event_name, handler)
        self._handler = handler

    def detach(
        self, page: EventTriggeredCapturePage
    ) -> None:
        if self._handler is None:
            return
        page.remove_listener(self.event_name, self._handler)
        self._handler = None

    async def flush(self) -> None:
        if not self._pending:
            return
        await asyncio.gather(
            *list(self._pending),
            return_exceptions=True,
        )


__all__ = [
    "EventTriggeredCaptureCollector",
    "EventTriggeredCapturePage",
]
