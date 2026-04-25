"""
Unit tests for RunArtifactLayout path construction.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

import pytest
from evaluate_agent.artifact_layout import (
    RUN_ID_FORMAT,
    InvalidRunId,
    RunArtifactLayout,
)


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


class TestAutoScreenshotPaths:
    def _layout(self) -> RunArtifactLayout:
        return RunArtifactLayout(
            runs_root=Path("/tmp/runs"),
            agent_name="my-agent",
            run_id="20260424T000000Z",
        )

    def test_auto_screenshot_path_sits_in_case_dir(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_screenshot_path(
            "case_one", 1, "nav"
        )
        assert path.parent == layout.case_dir("case_one")

    def test_auto_screenshot_path_uses_auto_prefix(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_screenshot_path(
            "case_one", 1, "nav"
        )
        assert path.name == "auto-001-nav.png"

    def test_auto_screenshot_path_zero_pads_step_number(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_screenshot_path(
            "case_one", 7, "nav"
        )
        assert path.name == "auto-007-nav.png"

    def test_auto_screenshot_path_supports_large_step_numbers(
        self,
    ) -> None:
        layout = self._layout()
        path = layout.auto_screenshot_path(
            "case_one", 2048, "nav"
        )
        assert path.name == "auto-2048-nav.png"

    def test_auto_screenshot_and_explicit_screenshot_are_distinct(
        self,
    ) -> None:
        layout = self._layout()
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

    def test_auto_screenshot_and_auto_dom_share_label_but_differ_in_dir_and_extension(
        self,
    ) -> None:
        layout = self._layout()
        auto_screenshot = layout.auto_screenshot_path(
            "c", 1, "nav"
        )
        auto_dom = layout.auto_dom_snapshot_path(
            "c", 1, "nav"
        )
        assert auto_screenshot.stem == auto_dom.stem
        assert auto_screenshot.suffix == ".png"
        assert auto_dom.suffix == ".html"
        assert auto_screenshot.parent != auto_dom.parent
        assert auto_screenshot.parent == layout.case_dir(
            "c"
        )
        assert auto_dom.parent == layout.dom_snapshot_dir(
            "c"
        )

    def test_different_cases_get_separate_screenshot_paths(
        self,
    ) -> None:
        layout = self._layout()
        first = layout.auto_screenshot_path(
            "case_one", 1, "nav"
        )
        second = layout.auto_screenshot_path(
            "case_two", 1, "nav"
        )
        assert first != second
        assert first.parent != second.parent


class TestFromRunId:
    def test_constructs_layout_with_supplied_run_id(
        self,
    ) -> None:
        layout = RunArtifactLayout.from_run_id(
            agent_name="x",
            run_id="20260425T173000Z",
            runs_root=Path("/tmp/r"),
        )
        assert layout.run_id == "20260425T173000Z"
        assert layout.agent_name == "x"
        assert layout.runs_root == Path("/tmp/r")

    def test_run_dir_uses_supplied_run_id(self) -> None:
        layout = RunArtifactLayout.from_run_id(
            agent_name="x",
            run_id="20260425T173000Z",
            runs_root=Path("/tmp/r"),
        )
        assert layout.run_dir == Path(
            "/tmp/r/x/20260425T173000Z"
        )

    def test_defaults_runs_root_to_relative_runs_dir(
        self,
    ) -> None:
        layout = RunArtifactLayout.from_run_id(
            agent_name="x",
            run_id="20260101T000000Z",
        )
        assert layout.runs_root == Path("runs")

    def test_for_agent_and_from_run_id_agree_on_paths(
        self,
    ) -> None:
        fixed = datetime(
            2026, 4, 25, 17, 30, 0, tzinfo=timezone.utc
        )
        canonical = RunArtifactLayout.for_agent(
            agent_name="x",
            now=fixed,
            runs_root=Path("/tmp/r"),
        )
        replay = RunArtifactLayout.from_run_id(
            agent_name="x",
            run_id=canonical.run_id,
            runs_root=Path("/tmp/r"),
        )
        assert replay == canonical
        assert replay.case_dir("c") == canonical.case_dir(
            "c"
        )


class TestRunIdValidation:
    @pytest.mark.parametrize(
        "bad_run_id",
        [
            "",
            "20260425",
            "20260425T1730",
            "2026-04-25T17:30:00Z",
            "20260425T173000",
            "abc",
            "20269999T999999Z",
            "20260230T000000Z",
        ],
    )
    def test_post_init_rejects_malformed_run_id(
        self, bad_run_id: str
    ) -> None:
        with pytest.raises(InvalidRunId) as exc_info:
            RunArtifactLayout(
                runs_root=Path("/tmp"),
                agent_name="a",
                run_id=bad_run_id,
            )
        assert exc_info.value.value == bad_run_id

    def test_from_run_id_rejects_malformed_run_id(
        self,
    ) -> None:
        with pytest.raises(InvalidRunId):
            RunArtifactLayout.from_run_id(
                agent_name="a",
                run_id="not-a-run-id",
            )

    def test_invalid_run_id_message_names_format(
        self,
    ) -> None:
        with pytest.raises(InvalidRunId) as exc_info:
            RunArtifactLayout(
                runs_root=Path("/tmp"),
                agent_name="a",
                run_id="bogus",
            )
        text = str(exc_info.value)
        assert "YYYYMMDDTHHMMSSZ" in text
        assert "20260425T173000Z" in text
        assert "To proceed:" in text

    def test_run_id_format_constant_is_iso_compact_utc(
        self,
    ) -> None:
        assert RUN_ID_FORMAT == "%Y%m%dT%H%M%SZ"
        sample = datetime(
            2026, 4, 25, 17, 30, 0, tzinfo=timezone.utc
        )
        assert (
            sample.strftime(RUN_ID_FORMAT)
            == "20260425T173000Z"
        )


class TestImmutability:
    def test_layout_is_frozen(self) -> None:
        layout = RunArtifactLayout(
            runs_root=Path("/tmp"),
            agent_name="a",
            run_id="20260424T000000Z",
        )
        with pytest.raises(FrozenInstanceError):
            layout.runs_root = Path("/elsewhere")


class TestPublicConstants:
    def test_trace_subdir(self):
        from evaluate_agent.artifact_layout import (
            TRACE_SUBDIR,
        )

        assert TRACE_SUBDIR == "trace"

    def test_dom_snapshots_subdir(self):
        from evaluate_agent.artifact_layout import (
            DOM_SNAPSHOTS_SUBDIR,
        )

        assert DOM_SNAPSHOTS_SUBDIR == "dom"

    def test_explicit_dom_prefix(self):
        from evaluate_agent.artifact_layout import (
            EXPLICIT_DOM_PREFIX,
        )

        assert EXPLICIT_DOM_PREFIX == "step"

    def test_dom_snapshot_extension(self):
        from evaluate_agent.artifact_layout import (
            DOM_SNAPSHOT_EXT,
        )

        assert DOM_SNAPSHOT_EXT == "html"

    def test_constants_match_path_construction(
        self,
    ) -> None:
        from evaluate_agent.artifact_layout import (
            DOM_SNAPSHOT_EXT,
            DOM_SNAPSHOTS_SUBDIR,
            EXPLICIT_DOM_PREFIX,
            TRACE_SUBDIR,
        )

        layout = RunArtifactLayout(
            runs_root=Path("/tmp"),
            agent_name="a",
            run_id="20260424T000000Z",
        )
        path = layout.dom_snapshot_path(
            "case_x", 1, "after_submit"
        )
        assert path.parent.name == DOM_SNAPSHOTS_SUBDIR
        assert path.parent.parent.name == TRACE_SUBDIR
        assert path.name.startswith(
            f"{EXPLICIT_DOM_PREFIX}-"
        )
        assert path.suffix == f".{DOM_SNAPSHOT_EXT}"
