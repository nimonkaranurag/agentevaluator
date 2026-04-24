"""
Automatic DOM snapshot on every main-frame navigation.
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

from .artifact_layout import RunArtifactLayout
from .trace import PageEventEmitter

_NAVIGATED_EVENT = "framenavigated"
_AUTO_EVENT_SUFFIX = "nav"


class NavigatedFrame(Protocol):
    parent_frame: Any

    async def content(self) -> str: ...


class AutoDOMSnapshotCollectorAlreadyAttached(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "AutoDOMSnapshotCollector.attach was called while the collector is already attached to an emitter.\n"
            "To proceed, choose one:\n"
            "  (1) Call .detach(emitter) on the attached emitter, then .attach(new_emitter) on the replacement. The collector keeps its step counter and continues numbering automatic captures monotonically across the swap.\n"
            "  (2) Instantiate a separate AutoDOMSnapshotCollector and attach each one to its own emitter exactly once.\n"
            "A single collector multiplexed across emitters would interleave captures from unrelated sessions into the same DOM directory; the evaluator treats that as an ordering bug and rejects the trace."
        )


@dataclass
class AutoDOMSnapshotCollector:
    layout: RunArtifactLayout
    case_id: str
    _step: int = field(default=0, init=False, repr=False)
    _pending: set[asyncio.Task[Any]] = field(
        default_factory=set, init=False, repr=False
    )
    _handler: Callable[[Any], None] | None = field(
        default=None, init=False, repr=False
    )
    _attached_emitter: PageEventEmitter | None = field(
        default=None, init=False, repr=False
    )

    def attach(self, emitter: PageEventEmitter) -> None:
        if self._handler is not None:
            raise AutoDOMSnapshotCollectorAlreadyAttached()

        def on_navigated(frame: NavigatedFrame) -> None:
            if _is_subframe(frame):
                return
            self._step += 1
            step_number = self._step
            task = asyncio.ensure_future(
                self._capture_frame(frame, step_number)
            )
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)

        emitter.on(_NAVIGATED_EVENT, on_navigated)
        self._handler = on_navigated
        self._attached_emitter = emitter

    def detach(self, emitter: PageEventEmitter) -> None:
        if self._handler is None:
            return
        emitter.remove_listener(
            _NAVIGATED_EVENT, self._handler
        )
        self._handler = None
        self._attached_emitter = None

    async def flush(self) -> None:
        if not self._pending:
            return
        pending = list(self._pending)
        await asyncio.gather(
            *pending, return_exceptions=True
        )

    async def _capture_frame(
        self,
        frame: NavigatedFrame,
        step_number: int,
    ) -> Path:
        path = self.layout.auto_dom_snapshot_path(
            self.case_id,
            step_number,
            _AUTO_EVENT_SUFFIX,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        content = await frame.content()
        path.write_text(content, encoding="utf-8")
        return path


def _is_subframe(frame: NavigatedFrame) -> bool:
    return getattr(frame, "parent_frame", None) is not None


__all__ = [
    "AutoDOMSnapshotCollector",
    "AutoDOMSnapshotCollectorAlreadyAttached",
    "NavigatedFrame",
]
