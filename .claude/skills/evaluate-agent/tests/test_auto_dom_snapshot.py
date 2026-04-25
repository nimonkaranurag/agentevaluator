"""
Unit tests for AutoDOMSnapshotCollector lifecycle, main-frame filtering, step numbering, content persistence, and error recovery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest
from evaluate_agent.artifact_layout import (
    RunArtifactLayout,
)
from evaluate_agent.driver.auto_dom_snapshot import (
    AutoDOMSnapshotCollector,
    AutoDOMSnapshotCollectorAlreadyAttached,
)


@dataclass
class FakeFrame:
    html: str = (
        "<!doctype html><html><body>ok</body></html>"
    )
    parent_frame: Any = None
    content_calls: int = 0
    raise_on_content: BaseException | None = None

    async def content(self) -> str:
        self.content_calls += 1
        if self.raise_on_content is not None:
            raise self.raise_on_content
        return self.html


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
        for handler in list(self.registered.get(event, [])):
            handler(payload)


@pytest.fixture
def layout(tmp_path: Path) -> RunArtifactLayout:
    return RunArtifactLayout(
        runs_root=tmp_path,
        agent_name="test-agent",
        run_id="20260424T000000Z",
    )


class TestAttachRegistersFrameNavigatedHandler:
    async def test_attach_registers_exactly_one_handler(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        assert set(emitter.registered.keys()) == {
            "framenavigated"
        }
        assert (
            len(emitter.registered["framenavigated"]) == 1
        )
        collector.detach(emitter)
        await collector.flush()

    async def test_double_attach_raises_with_recovery(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        with pytest.raises(
            AutoDOMSnapshotCollectorAlreadyAttached
        ) as info:
            collector.attach(FakePageEmitter())
        message = str(info.value)
        assert "already attached" in message
        assert ".detach(emitter)" in message
        assert "to proceed" in message.lower()
        collector.detach(emitter)
        await collector.flush()

    async def test_detach_removes_handler(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        collector.detach(emitter)
        assert emitter.registered["framenavigated"] == []
        await collector.flush()

    async def test_detach_without_attach_is_a_noop(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.detach(emitter)
        assert emitter.registered == {}
        await collector.flush()


class TestMainFrameFilter:
    async def test_main_frame_event_triggers_capture(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        frame = FakeFrame()
        emitter.emit("framenavigated", frame)
        await collector.flush()
        collector.detach(emitter)
        expected = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        assert expected.exists()
        assert frame.content_calls == 1

    async def test_subframe_event_is_ignored(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        main_frame = FakeFrame()
        subframe = FakeFrame(parent_frame=main_frame)
        emitter.emit("framenavigated", subframe)
        await collector.flush()
        collector.detach(emitter)
        assert not layout.dom_snapshot_dir("c").exists()
        assert subframe.content_calls == 0

    async def test_subframe_does_not_advance_counter(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        main_frame = FakeFrame()
        emitter.emit(
            "framenavigated",
            FakeFrame(parent_frame=main_frame),
        )
        emitter.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(emitter)
        expected = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        assert expected.exists()


class TestStepNumbering:
    async def test_monotonic_increment_across_events(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        for _ in range(3):
            emitter.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(emitter)
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == [
            "auto-001-nav.html",
            "auto-002-nav.html",
            "auto-003-nav.html",
        ]

    async def test_counter_independent_per_collector(
        self, layout: RunArtifactLayout
    ) -> None:
        first_emitter = FakePageEmitter()
        second_emitter = FakePageEmitter()
        first = AutoDOMSnapshotCollector(
            layout=layout, case_id="case_one"
        )
        second = AutoDOMSnapshotCollector(
            layout=layout, case_id="case_two"
        )
        first.attach(first_emitter)
        second.attach(second_emitter)
        first_emitter.emit("framenavigated", FakeFrame())
        first_emitter.emit("framenavigated", FakeFrame())
        second_emitter.emit("framenavigated", FakeFrame())
        await first.flush()
        await second.flush()
        first.detach(first_emitter)
        second.detach(second_emitter)
        first_dir = layout.dom_snapshot_dir("case_one")
        second_dir = layout.dom_snapshot_dir("case_two")
        assert sorted(
            p.name for p in first_dir.iterdir()
        ) == [
            "auto-001-nav.html",
            "auto-002-nav.html",
        ]
        assert sorted(
            p.name for p in second_dir.iterdir()
        ) == ["auto-001-nav.html"]


class TestContentPersistence:
    async def test_writes_rendered_html_to_returned_path(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        frame = FakeFrame(
            html="<!doctype html><h1>hello</h1>"
        )
        emitter.emit("framenavigated", frame)
        await collector.flush()
        collector.detach(emitter)
        path = layout.auto_dom_snapshot_path("c", 1, "nav")
        assert path.read_text(encoding="utf-8") == (
            "<!doctype html><h1>hello</h1>"
        )

    async def test_preserves_non_ascii_characters(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        frame = FakeFrame(
            html="<p>héllo — 世界 — café ☕</p>"
        )
        emitter.emit("framenavigated", frame)
        await collector.flush()
        collector.detach(emitter)
        path = layout.auto_dom_snapshot_path("c", 1, "nav")
        assert path.read_text(encoding="utf-8") == (
            "<p>héllo — 世界 — café ☕</p>"
        )

    async def test_writes_to_shared_dom_dir(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        emitter.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(emitter)
        path = layout.auto_dom_snapshot_path("c", 1, "nav")
        assert path.parent == layout.dom_snapshot_dir("c")


class TestLifecycleAfterDetach:
    async def test_emit_after_detach_does_not_capture(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        emitter.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(emitter)
        late = FakeFrame()
        emitter.emit("framenavigated", late)
        await collector.flush()
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == ["auto-001-nav.html"]
        assert late.content_calls == 0

    async def test_detach_then_attach_continues_counter(
        self, layout: RunArtifactLayout
    ) -> None:
        first = FakePageEmitter()
        second = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(first)
        first.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(first)
        collector.attach(second)
        second.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(second)
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == [
            "auto-001-nav.html",
            "auto-002-nav.html",
        ]


class TestFlush:
    async def test_flush_with_no_pending_is_a_noop(
        self, layout: RunArtifactLayout
    ) -> None:
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        await collector.flush()
        assert not layout.dom_snapshot_dir("c").exists()

    async def test_flush_absorbs_capture_exceptions(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        exploding = FakeFrame(
            raise_on_content=RuntimeError("page closed")
        )
        emitter.emit("framenavigated", exploding)
        await collector.flush()
        collector.detach(emitter)
        failed_path = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        assert not failed_path.exists()

    async def test_flush_persists_successful_captures_even_when_one_fails(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        emitter.emit("framenavigated", FakeFrame())
        emitter.emit(
            "framenavigated",
            FakeFrame(
                raise_on_content=RuntimeError("boom")
            ),
        )
        emitter.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(emitter)
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == [
            "auto-001-nav.html",
            "auto-003-nav.html",
        ]


class TestCoexistenceWithExplicitSnapshots:
    async def test_auto_and_explicit_files_do_not_collide(
        self, layout: RunArtifactLayout
    ) -> None:
        emitter = FakePageEmitter()
        collector = AutoDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(emitter)
        emitter.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(emitter)
        auto_path = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        explicit_path = layout.dom_snapshot_path(
            "c", 1, "nav"
        )
        assert auto_path != explicit_path
        assert auto_path.name.startswith("auto-")
        assert explicit_path.name.startswith("step-")
        assert auto_path.parent == explicit_path.parent
