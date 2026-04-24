"""
Unit tests for RunArtifactLayout path construction.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

import pytest
from evaluate_agent.driver import RunArtifactLayout


class TestFactory:
    def test_formats_run_id_from_utc_now(
        self,
    ) -> None:
        fixed = datetime(
            2026,
            4,
            24,
            15,
            30,
            45,
            tzinfo=timezone.utc,
        )
        layout = RunArtifactLayout.for_agent(
            agent_name="x", now=fixed
        )
        assert layout.run_id == "20260424T153045Z"

    def test_defaults_runs_root_to_relative_runs_dir(
        self,
    ) -> None:
        layout = RunArtifactLayout.for_agent(
            agent_name="x",
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert layout.runs_root == Path("runs")


class TestPaths:
    def _layout(self) -> RunArtifactLayout:
        return RunArtifactLayout(
            runs_root=Path("/tmp/runs"),
            agent_name="my-agent",
            run_id="20260424T000000Z",
        )

    def test_run_dir(self) -> None:
        layout = self._layout()
        assert layout.run_dir == Path(
            "/tmp/runs/my-agent/20260424T000000Z"
        )

    def test_case_dir(self) -> None:
        layout = self._layout()
        assert layout.case_dir("case_one") == Path(
            "/tmp/runs/my-agent/20260424T000000Z/case_one"
        )

    def test_screenshot_path_zero_pads_step_number(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.screenshot_path(
            "case_one", 3, "landing"
        )
        assert path.name == "step-003-landing.png"
        assert path.parent == layout.case_dir("case_one")

    def test_screenshot_path_supports_large_step_numbers(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.screenshot_path("c", 1234, "lbl")
        assert path.name == "step-1234-lbl.png"


class TestImmutability:
    def test_layout_is_frozen(self) -> None:
        layout = RunArtifactLayout(
            runs_root=Path("/tmp"),
            agent_name="a",
            run_id="b",
        )
        with pytest.raises(FrozenInstanceError):
            layout.runs_root = Path("/elsewhere")
