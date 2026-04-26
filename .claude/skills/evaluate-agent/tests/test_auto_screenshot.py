"""
Unit tests for AutoScreenshotCollector lifecycle, main-frame filtering, step numbering, content persistence, error recovery, and coexistence with explicit screenshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest
from evaluate_agent.artifact_layout import (
    RunArtifactLayout,
)
from evaluate_agent.driver.capture.event_triggered.auto_screenshot import (
    AutoScreenshotCollector,
    AutoScreenshotCollectorAlreadyAttached,
)


@dataclass
class FakeFrame:
    parent_frame: Any = None


@dataclass
class FakePage:
    registered: dict[str, list[Callable[[Any], None]]] = (
        field(default_factory=dict)
    )
    screenshots_taken: list[str] = field(
        default_factory=list
    )
    raise_on_screenshot: BaseException | None = None
    raise_on_screenshot_calls: list[
        BaseException | None
    ] = field(default_factory=list)
    screenshot_payload: bytes = b"fake-png-bytes"

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

    async def screenshot(
        self, *, path: str
    ) -> bytes | None:
        per_call = (
            self.raise_on_screenshot_calls.pop(0)
            if self.raise_on_screenshot_calls
            else self.raise_on_screenshot
        )
        if per_call is not None:
            raise per_call
        Path(path).write_bytes(self.screenshot_payload)
        self.screenshots_taken.append(path)
        return self.screenshot_payload


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
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        assert set(page.registered.keys()) == {
            "framenavigated"
        }
        assert len(page.registered["framenavigated"]) == 1
        collector.detach(page)
        await collector.flush()

    async def test_double_attach_raises_with_recovery(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        with pytest.raises(
            AutoScreenshotCollectorAlreadyAttached
        ) as info:
            collector.attach(FakePage())
        message = str(info.value)
        assert "already attached" in message
        assert ".detach(page)" in message
        assert "to proceed" in message.lower()
        collector.detach(page)
        await collector.flush()

    async def test_detach_removes_handler(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        collector.detach(page)
        assert page.registered["framenavigated"] == []
        await collector.flush()

    async def test_detach_without_attach_is_a_noop(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.detach(page)
        assert page.registered == {}
        await collector.flush()


class TestMainFrameFilter:
    async def test_main_frame_event_triggers_capture(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        expected = layout.auto_screenshot_path(
            "c", 1, "nav"
        )
        assert expected.exists()
        assert page.screenshots_taken == [str(expected)]

    async def test_subframe_event_is_ignored(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        main_frame = FakeFrame()
        subframe = FakeFrame(parent_frame=main_frame)
        page.emit("framenavigated", subframe)
        await collector.flush()
        collector.detach(page)
        assert not layout.case_dir("c").exists()
        assert page.screenshots_taken == []

    async def test_subframe_does_not_advance_counter(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        main_frame = FakeFrame()
        page.emit(
            "framenavigated",
            FakeFrame(parent_frame=main_frame),
        )
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        expected = layout.auto_screenshot_path(
            "c", 1, "nav"
        )
        assert expected.exists()


class TestStepNumbering:
    async def test_monotonic_increment_across_events(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        for _ in range(3):
            page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        case_dir = layout.case_dir("c")
        filenames = sorted(
            p.name
            for p in case_dir.iterdir()
            if p.suffix == ".png"
        )
        assert filenames == [
            "auto-001-nav.png",
            "auto-002-nav.png",
            "auto-003-nav.png",
        ]

    async def test_counter_independent_per_collector(
        self, layout: RunArtifactLayout
    ) -> None:
        first_page = FakePage()
        second_page = FakePage()
        first = AutoScreenshotCollector(
            layout=layout, case_id="case_one"
        )
        second = AutoScreenshotCollector(
            layout=layout, case_id="case_two"
        )
        first.attach(first_page)
        second.attach(second_page)
        first_page.emit("framenavigated", FakeFrame())
        first_page.emit("framenavigated", FakeFrame())
        second_page.emit("framenavigated", FakeFrame())
        await first.flush()
        await second.flush()
        first.detach(first_page)
        second.detach(second_page)
        first_dir = layout.case_dir("case_one")
        second_dir = layout.case_dir("case_two")
        assert sorted(
            p.name
            for p in first_dir.iterdir()
            if p.suffix == ".png"
        ) == [
            "auto-001-nav.png",
            "auto-002-nav.png",
        ]
        assert sorted(
            p.name
            for p in second_dir.iterdir()
            if p.suffix == ".png"
        ) == ["auto-001-nav.png"]


class TestContentPersistence:
    async def test_writes_screenshot_payload_to_returned_path(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage(
            screenshot_payload=b"PNG-magic-bytes-here"
        )
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        path = layout.auto_screenshot_path("c", 1, "nav")
        assert path.read_bytes() == b"PNG-magic-bytes-here"

    async def test_writes_to_case_dir_root(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        path = layout.auto_screenshot_path("c", 1, "nav")
        assert path.parent == layout.case_dir("c")

    async def test_creates_case_dir_lazily(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="lazy_case"
        )
        assert not layout.case_dir("lazy_case").exists()
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        assert layout.case_dir("lazy_case").is_dir()


class TestLifecycleAfterDetach:
    async def test_emit_after_detach_does_not_capture(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        case_dir = layout.case_dir("c")
        filenames = sorted(
            p.name
            for p in case_dir.iterdir()
            if p.suffix == ".png"
        )
        assert filenames == ["auto-001-nav.png"]
        assert len(page.screenshots_taken) == 1

    async def test_detach_then_attach_continues_counter(
        self, layout: RunArtifactLayout
    ) -> None:
        first = FakePage()
        second = FakePage()
        collector = AutoScreenshotCollector(
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
        case_dir = layout.case_dir("c")
        filenames = sorted(
            p.name
            for p in case_dir.iterdir()
            if p.suffix == ".png"
        )
        assert filenames == [
            "auto-001-nav.png",
            "auto-002-nav.png",
        ]


class TestFlush:
    async def test_flush_with_no_pending_is_a_noop(
        self, layout: RunArtifactLayout
    ) -> None:
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        await collector.flush()
        assert not layout.case_dir("c").exists()

    async def test_flush_absorbs_capture_exceptions(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage(
            raise_on_screenshot=RuntimeError("page closed")
        )
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        failed_path = layout.auto_screenshot_path(
            "c", 1, "nav"
        )
        assert not failed_path.exists()
        assert page.screenshots_taken == []

    async def test_flush_persists_successful_captures_even_when_one_fails(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        page = FakePage(
            raise_on_screenshot_calls=[
                None,
                RuntimeError("boom"),
                None,
            ]
        )
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        page.emit("framenavigated", FakeFrame())
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        case_dir = layout.case_dir("c")
        filenames = sorted(
            p.name
            for p in case_dir.iterdir()
            if p.suffix == ".png"
        )
        assert filenames == [
            "auto-001-nav.png",
            "auto-003-nav.png",
        ]


class TestCoexistenceWithExplicitScreenshots:
    async def test_auto_and_explicit_files_share_dir_without_collision(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        auto_path = layout.auto_screenshot_path(
            "c", 1, "nav"
        )
        explicit_path = layout.screenshot_path(
            "c", 1, "nav"
        )
        assert auto_path != explicit_path
        assert auto_path.name.startswith("auto-")
        assert explicit_path.name.startswith("step-")
        assert auto_path.parent == explicit_path.parent

    async def test_auto_screenshot_pairs_with_auto_dom_step_number_independently(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        page = FakePage()
        collector = AutoScreenshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("framenavigated", FakeFrame())
        await collector.flush()
        collector.detach(page)
        auto_screenshot = layout.auto_screenshot_path(
            "c", 1, "nav"
        )
        auto_dom = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        assert auto_screenshot.exists()
        assert auto_screenshot.stem == auto_dom.stem
        assert auto_screenshot.suffix == ".png"
        assert auto_dom.suffix == ".html"
