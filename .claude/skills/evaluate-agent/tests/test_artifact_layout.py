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


class TestTracePaths:
    def _layout(self) -> RunArtifactLayout:
        return RunArtifactLayout(
            runs_root=Path("/tmp/runs"),
            agent_name="my-agent",
            run_id="20260424T000000Z",
        )

    def test_trace_dir_lives_under_case_dir(
        self,
    ) -> None:
        layout = self._layout()
        paths = layout.trace_paths("case_one")
        assert (
            paths.trace_dir
            == layout.case_dir("case_one") / "trace"
        )

    def test_har_filename_is_network_har(self) -> None:
        layout = self._layout()
        paths = layout.trace_paths("case_one")
        assert paths.har_path.name == "network.har"
        assert paths.har_path.parent == paths.trace_dir

    def test_jsonl_streams_sit_alongside_har(
        self,
    ) -> None:
        layout = self._layout()
        paths = layout.trace_paths("case_one")
        for streaming_path, expected_name in (
            (paths.requests_path, "requests.jsonl"),
            (paths.responses_path, "responses.jsonl"),
            (paths.console_path, "console.jsonl"),
            (
                paths.page_errors_path,
                "page_errors.jsonl",
            ),
        ):
            assert streaming_path.name == expected_name
            assert streaming_path.parent == paths.trace_dir

    def test_different_cases_get_separate_trace_dirs(
        self,
    ) -> None:
        layout = self._layout()
        first = layout.trace_paths("case_one")
        second = layout.trace_paths("case_two")
        assert first.trace_dir != second.trace_dir


class TestDOMSnapshotPaths:
    def _layout(self) -> RunArtifactLayout:
        return RunArtifactLayout(
            runs_root=Path("/tmp/runs"),
            agent_name="my-agent",
            run_id="20260424T000000Z",
        )

    def test_dom_snapshot_dir_sits_under_trace(
        self,
    ) -> None:
        layout = self._layout()
        assert (
            layout.dom_snapshot_dir("case_one")
            == layout.case_dir("case_one") / "trace" / "dom"
        )

    def test_dom_snapshot_path_zero_pads_step_number(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.dom_snapshot_path(
            "case_one", 3, "landing"
        )
        assert path.name == "step-003-landing.html"
        assert path.parent == layout.dom_snapshot_dir(
            "case_one"
        )

    def test_dom_snapshot_path_supports_large_step_numbers(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.dom_snapshot_path(
            "case_one", 1234, "final"
        )
        assert path.name == "step-1234-final.html"

    def test_different_cases_get_separate_dom_dirs(
        self,
    ) -> None:
        layout = self._layout()
        first = layout.dom_snapshot_dir("case_one")
        second = layout.dom_snapshot_dir("case_two")
        assert first != second


class TestAutoDOMSnapshotPaths:
    def _layout(self) -> RunArtifactLayout:
        return RunArtifactLayout(
            runs_root=Path("/tmp/runs"),
            agent_name="my-agent",
            run_id="20260424T000000Z",
        )

    def test_auto_dom_snapshot_path_sits_in_shared_dom_dir(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_dom_snapshot_path(
            "case_one", 1, "nav"
        )
        assert path.parent == layout.dom_snapshot_dir(
            "case_one"
        )

    def test_auto_dom_snapshot_path_uses_auto_prefix(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_dom_snapshot_path(
            "case_one", 1, "nav"
        )
        assert path.name == "auto-001-nav.html"

    def test_auto_dom_snapshot_path_zero_pads_step_number(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_dom_snapshot_path(
            "case_one", 7, "nav"
        )
        assert path.name == "auto-007-nav.html"

    def test_auto_dom_snapshot_path_supports_large_step_numbers(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_dom_snapshot_path(
            "case_one", 2048, "nav"
        )
        assert path.name == "auto-2048-nav.html"

    def test_auto_and_explicit_paths_are_distinct(
        self,
    ) -> None:
        layout = self._layout()
        auto_path = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        explicit_path = layout.dom_snapshot_path(
            "c", 1, "nav"
        )
        assert auto_path != explicit_path
        assert auto_path.name.startswith("auto-")
        assert explicit_path.name.startswith("step-")


class TestImmutability:
    def test_layout_is_frozen(self) -> None:
        layout = RunArtifactLayout(
            runs_root=Path("/tmp"),
            agent_name="a",
            run_id="b",
        )
        with pytest.raises(FrozenInstanceError):
            layout.runs_root = Path("/elsewhere")
