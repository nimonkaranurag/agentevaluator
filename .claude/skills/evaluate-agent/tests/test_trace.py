"""
Unit tests for TraceArtifactPaths, TraceCollector, and collect_trace.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest
from evaluate_agent.driver.trace import (
    TraceArtifactPaths,
    TraceCollector,
    TraceCollectorAlreadyAttached,
    collect_trace,
)


@dataclass
class FakeRequest:
    method: str
    url: str
    resource_type: str
    headers: dict[str, str]


@dataclass
class FakeResponse:
    url: str
    status: int
    status_text: str
    headers: dict[str, str]


@dataclass
class FakeConsoleMessage:
    type: str
    text: str
    location: dict[str, Any]


@dataclass
class FakePageEmitter:
    registered: dict[str, list[Callable[[Any], None]]] = (
        field(default_factory=dict)
    )

    def on(
        self,
        event: str,
        handler: Callable[[Any], None],
    ) -> None:
        self.registered.setdefault(event, []).append(
            handler
        )

    def remove_listener(
        self,
        event: str,
        handler: Callable[[Any], None],
    ) -> None:
        self.registered.get(event, []).remove(handler)

    def emit(self, event: str, payload: Any) -> None:
        for handler in self.registered.get(event, []):
            handler(payload)


@pytest.fixture
def trace_paths(tmp_path: Path) -> TraceArtifactPaths:
    trace_dir = tmp_path / "case" / "trace"
    return TraceArtifactPaths(
        trace_dir=trace_dir,
        har_path=trace_dir / "network.har",
        requests_path=trace_dir / "requests.jsonl",
        responses_path=trace_dir / "responses.jsonl",
        console_path=trace_dir / "console.jsonl",
        page_errors_path=trace_dir / "page_errors.jsonl",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


class TestTraceArtifactPaths:
    def test_ensure_dir_creates_nested_directory(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        assert not trace_paths.trace_dir.exists()
        trace_paths.ensure_dir()
        assert trace_paths.trace_dir.is_dir()

    def test_ensure_dir_is_idempotent(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        trace_paths.ensure_dir()
        trace_paths.ensure_dir()
        assert trace_paths.trace_dir.is_dir()

    def test_paths_are_frozen(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            trace_paths.trace_dir = Path("/elsewhere")


class TestCollectTraceLifecycle:
    async def test_creates_streaming_files_on_enter(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        async with collect_trace(trace_paths):
            assert trace_paths.requests_path.exists()
            assert trace_paths.responses_path.exists()
            assert trace_paths.console_path.exists()
            assert trace_paths.page_errors_path.exists()

    async def test_closes_handles_on_exit(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        async with collect_trace(trace_paths) as collector:
            pass
        assert collector.requests_handle.closed
        assert collector.responses_handle.closed
        assert collector.console_handle.closed
        assert collector.page_errors_handle.closed

    async def test_closes_handles_on_exception_inside_block(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        collector_ref: list[TraceCollector] = []
        with pytest.raises(RuntimeError):
            async with collect_trace(
                trace_paths
            ) as collector:
                collector_ref.append(collector)
                raise RuntimeError("boom")
        collector = collector_ref[0]
        assert collector.requests_handle.closed

    async def test_detach_without_attach_is_a_noop(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.detach(emitter)
        assert emitter.registered == {}


class TestAttachRegistersHandlers:
    async def test_attach_registers_four_page_events(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            assert set(emitter.registered.keys()) == {
                "request",
                "response",
                "console",
                "pageerror",
            }
            assert all(
                len(handlers) == 1
                for handlers in emitter.registered.values()
            )

    async def test_double_attach_raises_with_recovery(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            with pytest.raises(
                TraceCollectorAlreadyAttached
            ) as info:
                collector.attach(FakePageEmitter())
        assert "already attached" in str(info.value)
        assert ".detach(emitter)" in str(info.value)

    async def test_detach_removes_all_handlers(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            collector.detach(emitter)
        assert all(
            handlers == []
            for handlers in emitter.registered.values()
        )


class TestEventWritesJsonl:
    async def test_request_event_emits_a_jsonl_line(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            emitter.emit(
                "request",
                FakeRequest(
                    method="GET",
                    url="https://example.test/",
                    resource_type="document",
                    headers={"accept": "text/html"},
                ),
            )
            collector.detach(emitter)
        lines = _read_jsonl(trace_paths.requests_path)
        assert len(lines) == 1
        entry = lines[0]
        assert entry["method"] == "GET"
        assert entry["url"] == "https://example.test/"
        assert entry["resource_type"] == "document"
        assert entry["headers"] == {"accept": "text/html"}
        assert "ts" in entry

    async def test_response_event_emits_a_jsonl_line(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            emitter.emit(
                "response",
                FakeResponse(
                    url="https://example.test/",
                    status=200,
                    status_text="OK",
                    headers={"content-type": "text/html"},
                ),
            )
            collector.detach(emitter)
        lines = _read_jsonl(trace_paths.responses_path)
        assert len(lines) == 1
        entry = lines[0]
        assert entry["url"] == "https://example.test/"
        assert entry["status"] == 200
        assert entry["status_text"] == "OK"

    async def test_console_event_emits_a_jsonl_line(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            emitter.emit(
                "console",
                FakeConsoleMessage(
                    type="warning",
                    text="deprecated API",
                    location={
                        "url": "https://example.test/app.js",
                        "lineNumber": 42,
                    },
                ),
            )
            collector.detach(emitter)
        lines = _read_jsonl(trace_paths.console_path)
        assert len(lines) == 1
        entry = lines[0]
        assert entry["type"] == "warning"
        assert entry["text"] == "deprecated API"
        assert entry["location"] == {
            "url": "https://example.test/app.js",
            "lineNumber": 42,
        }

    async def test_page_error_event_emits_a_jsonl_line(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            emitter.emit(
                "pageerror",
                RuntimeError("oh no"),
            )
            collector.detach(emitter)
        lines = _read_jsonl(trace_paths.page_errors_path)
        assert len(lines) == 1
        assert lines[0]["message"] == "oh no"

    async def test_detached_emitter_no_longer_writes(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            emitter.emit(
                "request",
                FakeRequest(
                    method="GET",
                    url="https://one/",
                    resource_type="document",
                    headers={},
                ),
            )
            collector.detach(emitter)
            emitter.emit(
                "request",
                FakeRequest(
                    method="GET",
                    url="https://two/",
                    resource_type="document",
                    headers={},
                ),
            )
        lines = _read_jsonl(trace_paths.requests_path)
        assert [e["url"] for e in lines] == ["https://one/"]

    async def test_events_preserve_order_across_streams(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        emitter = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(emitter)
            for index in range(3):
                emitter.emit(
                    "request",
                    FakeRequest(
                        method="GET",
                        url=f"https://example.test/{index}",
                        resource_type="document",
                        headers={},
                    ),
                )
            collector.detach(emitter)
        lines = _read_jsonl(trace_paths.requests_path)
        assert [e["url"] for e in lines] == [
            "https://example.test/0",
            "https://example.test/1",
            "https://example.test/2",
        ]


class TestReattachAfterDetach:
    async def test_detach_then_attach_to_different_emitter(
        self, trace_paths: TraceArtifactPaths
    ) -> None:
        first = FakePageEmitter()
        second = FakePageEmitter()
        async with collect_trace(trace_paths) as collector:
            collector.attach(first)
            first.emit(
                "request",
                FakeRequest(
                    method="GET",
                    url="https://first/",
                    resource_type="document",
                    headers={},
                ),
            )
            collector.detach(first)
            collector.attach(second)
            second.emit(
                "request",
                FakeRequest(
                    method="GET",
                    url="https://second/",
                    resource_type="document",
                    headers={},
                ),
            )
            collector.detach(second)
        lines = _read_jsonl(trace_paths.requests_path)
        assert [e["url"] for e in lines] == [
            "https://first/",
            "https://second/",
        ]
