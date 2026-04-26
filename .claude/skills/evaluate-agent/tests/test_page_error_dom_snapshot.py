"""
Unit tests for PageErrorDOMSnapshotCollector lifecycle, step numbering, content persistence, and error recovery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest
from evaluate_agent.artifact_layout import (
    RunArtifactLayout,
)
from evaluate_agent.driver.capture.event_triggered.page_error_dom_snapshot import (
    PageErrorDOMSnapshotCollector,
    PageErrorDOMSnapshotCollectorAlreadyAttached,
)


@dataclass
class FakePage:
    html: str = (
        "<!doctype html><html><body>ok</body></html>"
    )
    content_calls: int = 0
    raise_on_content: BaseException | None = None
    raise_on_content_calls: list[BaseException | None] = (
        field(default_factory=list)
    )
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

    async def content(self) -> str:
        self.content_calls += 1
        per_call = (
            self.raise_on_content_calls.pop(0)
            if self.raise_on_content_calls
            else self.raise_on_content
        )
        if per_call is not None:
            raise per_call
        return self.html


@pytest.fixture
def layout(tmp_path: Path) -> RunArtifactLayout:
    return RunArtifactLayout(
        runs_root=tmp_path,
        agent_name="test-agent",
        run_id="20260424T000000Z",
    )


class TestAttachRegistersPageErrorHandler:
    async def test_attach_registers_exactly_one_handler(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        assert set(page.registered.keys()) == {"pageerror"}
        assert len(page.registered["pageerror"]) == 1
        collector.detach(page)
        await collector.flush()

    async def test_double_attach_raises_with_recovery(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        with pytest.raises(
            PageErrorDOMSnapshotCollectorAlreadyAttached
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
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        collector.detach(page)
        assert page.registered["pageerror"] == []
        await collector.flush()

    async def test_detach_without_attach_is_a_noop(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.detach(page)
        assert page.registered == {}
        await collector.flush()


class TestPageErrorEventTriggersCapture:
    async def test_pageerror_with_string_payload_captures_dom(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage(
            html="<!doctype html><h1>broken</h1>"
        )
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "TypeError: x is undefined")
        await collector.flush()
        collector.detach(page)
        expected = layout.auto_dom_snapshot_path(
            "c", 1, "pageerror"
        )
        assert expected.exists()
        assert expected.read_text(encoding="utf-8") == (
            "<!doctype html><h1>broken</h1>"
        )

    async def test_pageerror_with_error_object_payload_captures_dom(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", RuntimeError("oops"))
        await collector.flush()
        collector.detach(page)
        expected = layout.auto_dom_snapshot_path(
            "c", 1, "pageerror"
        )
        assert expected.exists()


class TestStepNumbering:
    async def test_first_capture_is_step_001(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(page)
        assert layout.auto_dom_snapshot_path(
            "c", 1, "pageerror"
        ).exists()

    async def test_monotonic_increment_across_events(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        for _ in range(3):
            page.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(page)
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == [
            "auto-001-pageerror.html",
            "auto-002-pageerror.html",
            "auto-003-pageerror.html",
        ]

    async def test_counter_independent_per_collector(
        self, layout: RunArtifactLayout
    ) -> None:
        first_page = FakePage()
        second_page = FakePage()
        first = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="case_one"
        )
        second = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="case_two"
        )
        first.attach(first_page)
        second.attach(second_page)
        first_page.emit("pageerror", "E")
        first_page.emit("pageerror", "E")
        second_page.emit("pageerror", "E")
        await first.flush()
        await second.flush()
        first.detach(first_page)
        second.detach(second_page)
        first_dir = layout.dom_snapshot_dir("case_one")
        second_dir = layout.dom_snapshot_dir("case_two")
        assert sorted(
            p.name for p in first_dir.iterdir()
        ) == [
            "auto-001-pageerror.html",
            "auto-002-pageerror.html",
        ]
        assert sorted(
            p.name for p in second_dir.iterdir()
        ) == ["auto-001-pageerror.html"]


class TestContentPersistence:
    async def test_writes_rendered_html_to_returned_path(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage(
            html="<!doctype html><h1>broken</h1>"
        )
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(page)
        path = layout.auto_dom_snapshot_path(
            "c", 1, "pageerror"
        )
        assert path.read_text(encoding="utf-8") == (
            "<!doctype html><h1>broken</h1>"
        )

    async def test_preserves_non_ascii_characters(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage(
            html="<p>héllo — 世界 — café ☕</p>"
        )
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(page)
        path = layout.auto_dom_snapshot_path(
            "c", 1, "pageerror"
        )
        assert path.read_text(encoding="utf-8") == (
            "<p>héllo — 世界 — café ☕</p>"
        )


class TestLifecycleAfterDetach:
    async def test_emit_after_detach_does_not_capture(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(page)
        page.emit("pageerror", "Error")
        await collector.flush()
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == ["auto-001-pageerror.html"]
        assert page.content_calls == 1

    async def test_detach_then_attach_continues_counter(
        self, layout: RunArtifactLayout
    ) -> None:
        first = FakePage()
        second = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(first)
        first.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(first)
        collector.attach(second)
        second.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(second)
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == [
            "auto-001-pageerror.html",
            "auto-002-pageerror.html",
        ]


class TestFlush:
    async def test_flush_with_no_pending_is_a_noop(
        self, layout: RunArtifactLayout
    ) -> None:
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        await collector.flush()
        assert not layout.dom_snapshot_dir("c").exists()

    async def test_flush_absorbs_capture_exceptions(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage(
            raise_on_content=RuntimeError("page closed")
        )
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(page)
        failed_path = layout.auto_dom_snapshot_path(
            "c", 1, "pageerror"
        )
        assert not failed_path.exists()

    async def test_flush_persists_successful_captures_even_when_one_fails(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage(
            raise_on_content_calls=[
                None,
                RuntimeError("boom"),
                None,
            ]
        )
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "E")
        page.emit("pageerror", "E")
        page.emit("pageerror", "E")
        await collector.flush()
        collector.detach(page)
        dom_dir = layout.dom_snapshot_dir("c")
        filenames = sorted(
            p.name for p in dom_dir.iterdir()
        )
        assert filenames == [
            "auto-001-pageerror.html",
            "auto-003-pageerror.html",
        ]


class TestCoexistenceWithNavSnapshots:
    async def test_pageerror_and_nav_files_share_dir_without_collision(
        self, layout: RunArtifactLayout
    ) -> None:
        page = FakePage()
        collector = PageErrorDOMSnapshotCollector(
            layout=layout, case_id="c"
        )
        collector.attach(page)
        page.emit("pageerror", "Error")
        await collector.flush()
        collector.detach(page)
        pageerror_path = layout.auto_dom_snapshot_path(
            "c", 1, "pageerror"
        )
        nav_path = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        assert pageerror_path != nav_path
        assert pageerror_path.parent == nav_path.parent
        assert pageerror_path.name == (
            "auto-001-pageerror.html"
        )
        assert nav_path.name == "auto-001-nav.html"
