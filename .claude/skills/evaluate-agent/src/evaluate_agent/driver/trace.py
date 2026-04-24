"""
Baseline capture of Playwright page events to streaming artifacts.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Protocol,
    TextIO,
    runtime_checkable,
)


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


@runtime_checkable
class PageEventEmitter(Protocol):
    def on(
        self,
        event: str,
        handler: Callable[[Any], None],
    ) -> None: ...

    def remove_listener(
        self,
        event: str,
        handler: Callable[[Any], None],
    ) -> None: ...


class TraceCollectorAlreadyAttached(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "TraceCollector.attach was called while the collector is already attached to an emitter.\n"
            "To proceed, choose one:\n"
            "  (1) Call .detach(emitter) on the attached emitter, then .attach(new_emitter) on the replacement. The collector re-uses its open file handles, so the JSONL streams remain continuous across the swap.\n"
            "  (2) Construct a separate collector via a nested `async with collect_trace(other_trace_paths) as other_collector` block and attach each one to its own emitter exactly once.\n"
            "A single collector multiplexed across emitters would interleave events from unrelated sessions into the same JSONL stream; the evaluator treats that as an ordering bug and rejects the trace."
        )


_REQUEST_EVENT = "request"
_RESPONSE_EVENT = "response"
_CONSOLE_EVENT = "console"
_PAGE_ERROR_EVENT = "pageerror"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(
        timespec="milliseconds"
    )


def _write_jsonl(
    handle: TextIO, payload: dict[str, Any]
) -> None:
    handle.write(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    handle.write("\n")
    handle.flush()


def _request_event_payload(
    request: Any,
) -> dict[str, Any]:
    return {
        "ts": _utc_now_iso(),
        "method": getattr(request, "method", None),
        "url": getattr(request, "url", None),
        "resource_type": getattr(
            request, "resource_type", None
        ),
        "headers": dict(
            getattr(request, "headers", {}) or {}
        ),
    }


def _response_event_payload(
    response: Any,
) -> dict[str, Any]:
    return {
        "ts": _utc_now_iso(),
        "url": getattr(response, "url", None),
        "status": getattr(response, "status", None),
        "status_text": getattr(
            response, "status_text", None
        ),
        "headers": dict(
            getattr(response, "headers", {}) or {}
        ),
    }


def _console_event_payload(
    message: Any,
) -> dict[str, Any]:
    location = getattr(message, "location", {}) or {}
    return {
        "ts": _utc_now_iso(),
        "type": getattr(message, "type", None),
        "text": getattr(message, "text", None),
        "location": (
            dict(location)
            if isinstance(location, dict)
            else {}
        ),
    }


def _page_error_event_payload(
    error: Any,
) -> dict[str, Any]:
    return {
        "ts": _utc_now_iso(),
        "message": str(error),
    }


@dataclass
class _AttachedHandlers:
    on_request: Callable[[Any], None]
    on_response: Callable[[Any], None]
    on_console: Callable[[Any], None]
    on_page_error: Callable[[Any], None]


@dataclass(kw_only=True)
class TraceCollector:
    requests_handle: TextIO
    responses_handle: TextIO
    console_handle: TextIO
    page_errors_handle: TextIO
    _attached: _AttachedHandlers | None = field(
        default=None, init=False, repr=False
    )
    _attached_emitter: PageEventEmitter | None = field(
        default=None, init=False, repr=False
    )

    def attach(self, emitter: PageEventEmitter) -> None:
        if self._attached is not None:
            raise TraceCollectorAlreadyAttached()
        handlers = _AttachedHandlers(
            on_request=lambda r: _write_jsonl(
                self.requests_handle,
                _request_event_payload(r),
            ),
            on_response=lambda r: _write_jsonl(
                self.responses_handle,
                _response_event_payload(r),
            ),
            on_console=lambda m: _write_jsonl(
                self.console_handle,
                _console_event_payload(m),
            ),
            on_page_error=lambda e: _write_jsonl(
                self.page_errors_handle,
                _page_error_event_payload(e),
            ),
        )
        emitter.on(_REQUEST_EVENT, handlers.on_request)
        emitter.on(_RESPONSE_EVENT, handlers.on_response)
        emitter.on(_CONSOLE_EVENT, handlers.on_console)
        emitter.on(
            _PAGE_ERROR_EVENT,
            handlers.on_page_error,
        )
        self._attached = handlers
        self._attached_emitter = emitter

    def detach(self, emitter: PageEventEmitter) -> None:
        if (
            self._attached is None
            or self._attached_emitter is None
        ):
            return
        emitter.remove_listener(
            _REQUEST_EVENT, self._attached.on_request
        )
        emitter.remove_listener(
            _RESPONSE_EVENT,
            self._attached.on_response,
        )
        emitter.remove_listener(
            _CONSOLE_EVENT, self._attached.on_console
        )
        emitter.remove_listener(
            _PAGE_ERROR_EVENT,
            self._attached.on_page_error,
        )
        self._attached = None
        self._attached_emitter = None


@asynccontextmanager
async def collect_trace(
    trace_paths: TraceArtifactPaths,
) -> AsyncIterator[TraceCollector]:
    trace_paths.ensure_dir()
    requests_handle = trace_paths.requests_path.open(
        "w", encoding="utf-8"
    )
    responses_handle = trace_paths.responses_path.open(
        "w", encoding="utf-8"
    )
    console_handle = trace_paths.console_path.open(
        "w", encoding="utf-8"
    )
    page_errors_handle = trace_paths.page_errors_path.open(
        "w", encoding="utf-8"
    )
    collector = TraceCollector(
        requests_handle=requests_handle,
        responses_handle=responses_handle,
        console_handle=console_handle,
        page_errors_handle=page_errors_handle,
    )
    try:
        yield collector
    finally:
        for handle in (
            requests_handle,
            responses_handle,
            console_handle,
            page_errors_handle,
        ):
            try:
                handle.close()
            except Exception:
                pass


__all__ = [
    "PageEventEmitter",
    "TraceArtifactPaths",
    "TraceCollector",
    "TraceCollectorAlreadyAttached",
    "collect_trace",
]
