"""
Unit tests for DOMSnapshotter step numbering, artifact paths, content persistence, and label validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from evaluate_agent.artifact_layout import (
    RunArtifactLayout,
)
from evaluate_agent.driver.dom_snapshot import (
    DOMSnapshotter,
    InvalidDOMSnapshotLabel,
)


@dataclass
class FakePage:
    html: str = (
        "<!doctype html><html><body>ok</body></html>"
    )
    content_calls: int = 0
    returned_payloads: list[str] = field(
        default_factory=list
    )

    async def content(self) -> str:
        self.content_calls += 1
        self.returned_payloads.append(self.html)
        return self.html


@pytest.fixture
def layout(tmp_path: Path) -> RunArtifactLayout:
    return RunArtifactLayout(
        runs_root=tmp_path,
        agent_name="test-agent",
        run_id="20260424T000000Z",
    )


class TestStepNumbering:
    async def test_first_snapshot_is_step_001(
        self, layout: RunArtifactLayout
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        path = await snapshotter.snapshot(
            FakePage(), "landing"
        )
        assert path.name == "step-001-landing.html"

    async def test_step_counter_increments_across_calls(
        self, layout: RunArtifactLayout
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        page = FakePage()
        p1 = await snapshotter.snapshot(page, "a")
        p2 = await snapshotter.snapshot(page, "b")
        p3 = await snapshotter.snapshot(page, "c")
        assert p1.name == "step-001-a.html"
        assert p2.name == "step-002-b.html"
        assert p3.name == "step-003-c.html"

    async def test_step_counter_is_independent_per_instance(
        self, layout: RunArtifactLayout
    ) -> None:
        first = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        second = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        await first.snapshot(FakePage(), "one")
        await first.snapshot(FakePage(), "two")
        path_from_second = await second.snapshot(
            FakePage(), "three"
        )
        assert (
            path_from_second.name == "step-001-three.html"
        )


class TestArtifactPath:
    async def test_creates_dom_subdir_under_trace_lazily(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        path = await snapshotter.snapshot(
            FakePage(), "landing"
        )
        assert path.parent.is_dir()
        assert path.parent.name == "dom"
        assert path.parent.parent.name == "trace"

    async def test_path_matches_layout_contract(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        path = await snapshotter.snapshot(
            FakePage(), "landing"
        )
        assert path == layout.dom_snapshot_path(
            "case", 1, "landing"
        )

    async def test_different_cases_get_separate_dom_dirs(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        first = DOMSnapshotter(
            layout=layout, case_id="case_one"
        )
        second = DOMSnapshotter(
            layout=layout, case_id="case_two"
        )
        first_path = await first.snapshot(
            FakePage(), "landing"
        )
        second_path = await second.snapshot(
            FakePage(), "landing"
        )
        assert first_path.parent != second_path.parent


class TestContentPersistence:
    async def test_writes_rendered_html_to_returned_path(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        page = FakePage(
            html="<!doctype html><html><body><h1>hello</h1></body></html>"
        )
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        path = await snapshotter.snapshot(page, "landing")
        assert path.read_text(encoding="utf-8") == page.html

    async def test_preserves_non_ascii_characters(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        page = FakePage(
            html="<p>héllo — 世界 — café ☕</p>"
        )
        path = await snapshotter.snapshot(page, "landing")
        assert path.read_text(encoding="utf-8") == page.html

    async def test_calls_page_content_exactly_once(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        page = FakePage()
        await snapshotter.snapshot(page, "landing")
        assert page.content_calls == 1

    async def test_each_snapshot_rereads_content(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="case"
        )
        page = FakePage()
        await snapshotter.snapshot(page, "one")
        page.html = "<p>updated</p>"
        await snapshotter.snapshot(page, "two")
        assert page.content_calls == 2
        run_dir = layout.run_dir / "case" / "trace" / "dom"
        first_file = run_dir / "step-001-one.html"
        second_file = run_dir / "step-002-two.html"
        assert first_file.read_text(
            encoding="utf-8"
        ) != second_file.read_text(encoding="utf-8")
        assert (
            second_file.read_text(encoding="utf-8")
            == "<p>updated</p>"
        )


class TestLabelValidation:
    @pytest.mark.parametrize(
        "bad_label",
        [
            "Upper",
            "has space",
            "",
            "-lead",
            "9start",
            "trailing/slash",
            "dot.in.middle",
        ],
    )
    async def test_rejects_non_slug_labels(
        self,
        layout: RunArtifactLayout,
        bad_label: str,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="c"
        )
        with pytest.raises(InvalidDOMSnapshotLabel) as info:
            await snapshotter.snapshot(
                FakePage(), bad_label
            )
        assert info.value.label == bad_label
        assert (
            "filesystem-safe" in str(info.value)
            and "to proceed" in str(info.value).lower()
        )

    async def test_invalid_label_does_not_touch_filesystem(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="c"
        )
        with pytest.raises(InvalidDOMSnapshotLabel):
            await snapshotter.snapshot(
                FakePage(), "Invalid"
            )
        assert not layout.dom_snapshot_dir("c").exists()

    async def test_invalid_label_does_not_advance_counter(
        self,
        layout: RunArtifactLayout,
    ) -> None:
        snapshotter = DOMSnapshotter(
            layout=layout, case_id="c"
        )
        with pytest.raises(InvalidDOMSnapshotLabel):
            await snapshotter.snapshot(
                FakePage(), "Invalid"
            )
        first_good = await snapshotter.snapshot(
            FakePage(), "landing"
        )
        assert first_good.name == "step-001-landing.html"
