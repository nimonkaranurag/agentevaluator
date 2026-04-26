"""
Unit tests for Screenshotter step numbering, artifact paths, and label validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from evaluate_agent.artifact_layout import (
    RunArtifactLayout,
)
from evaluate_agent.driver.capture.explicit.screenshot import (
    InvalidScreenshotLabel,
    Screenshotter,
)


@dataclass
class FakePage:
    screenshots_taken: list[str] = field(
        default_factory=list
    )

    async def screenshot(self, *, path: str) -> None:
        Path(path).write_bytes(b"")
        self.screenshots_taken.append(path)


@pytest.fixture
def layout(tmp_path: Path) -> RunArtifactLayout:
    return RunArtifactLayout(
        runs_root=tmp_path,
        agent_name="test-agent",
        run_id="20260424T000000Z",
    )


class TestScreenshotStepNumbering:
    async def test_first_screenshot_is_step_001(
        self, layout: RunArtifactLayout
    ) -> None:
        screenshotter = Screenshotter(
            layout=layout, case_id="case"
        )
        path = await screenshotter.screenshot(
            FakePage(), "landing"
        )
        assert path.name == "step-001-landing.png"

    async def test_step_counter_increments_across_calls(
        self, layout: RunArtifactLayout
    ) -> None:
        screenshotter = Screenshotter(
            layout=layout, case_id="case"
        )
        page = FakePage()
        p1 = await screenshotter.screenshot(page, "a")
        p2 = await screenshotter.screenshot(page, "b")
        p3 = await screenshotter.screenshot(page, "c")
        assert p1.name == "step-001-a.png"
        assert p2.name == "step-002-b.png"
        assert p3.name == "step-003-c.png"


class TestArtifactPath:
    async def test_creates_case_directory_lazily(
        self, layout: RunArtifactLayout
    ) -> None:
        screenshotter = Screenshotter(
            layout=layout, case_id="case"
        )
        path = await screenshotter.screenshot(
            FakePage(), "landing"
        )
        assert path.parent.is_dir()
        assert path.exists()

    async def test_screenshot_written_to_returned_path(
        self, layout: RunArtifactLayout
    ) -> None:
        screenshotter = Screenshotter(
            layout=layout, case_id="case"
        )
        page = FakePage()
        path = await screenshotter.screenshot(
            page, "landing"
        )
        assert page.screenshots_taken == [str(path)]


class TestLabelValidation:
    @pytest.mark.parametrize(
        "bad_label",
        ["Upper", "has space", "", "-lead", "9start"],
    )
    async def test_rejects_non_slug_labels(
        self,
        layout: RunArtifactLayout,
        bad_label: str,
    ) -> None:
        screenshotter = Screenshotter(
            layout=layout, case_id="c"
        )
        with pytest.raises(InvalidScreenshotLabel):
            await screenshotter.screenshot(
                FakePage(), bad_label
            )
