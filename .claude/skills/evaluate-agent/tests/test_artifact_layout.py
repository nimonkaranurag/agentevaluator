"""
Failure-mode tests for run-id parsing, layout path composition, and owner-only directory creation.
"""

from __future__ import annotations

import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest
from evaluate_agent.artifact_layout import (
    DOM_SNAPSHOTS_SUBDIR,
    EXPLICIT_DOM_PREFIX,
    GENERATION_LOG_FILENAME,
    OBSERVABILITY_SUBDIR,
    OWNER_ONLY_MODE,
    ROUTING_DECISION_LOG_FILENAME,
    RUN_ID_FORMAT,
    STEP_COUNT_FILENAME,
    TOOL_CALL_LOG_FILENAME,
    TRACE_SUBDIR,
    InvalidRunId,
    RunArtifactLayout,
    create_owner_only_dir,
    parse_run_id,
)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "20260425",  # missing time
        "20260425T173000",  # missing UTC marker
        "2026-04-25T17:30:00Z",  # ISO-8601, not the layout shape
        "20261325T173000Z",  # bad month
    ],
)
def test_parse_run_id_rejects_malformed_inputs(
    value: str,
) -> None:
    with pytest.raises(InvalidRunId) as info:
        parse_run_id(value)
    assert info.value.value == value


def test_parse_run_id_accepts_canonical_shape() -> None:
    parse_run_id("20260425T173000Z")


def test_run_artifact_layout_for_agent_now_pins_run_id() -> (
    None
):
    fixed = datetime(
        2026, 4, 25, 17, 30, 0, tzinfo=timezone.utc
    )
    layout = RunArtifactLayout.for_agent(
        agent_name="demo", now=fixed
    )
    assert layout.run_id == fixed.strftime(RUN_ID_FORMAT)
    assert (
        layout.run_dir
        == Path("runs") / "demo" / "20260425T173000Z"
    )


def test_run_artifact_layout_from_run_id_validates() -> (
    None
):
    # Constructing with a malformed run_id must fail at __post_init__
    # so a CLI flag with a typo is rejected at the boundary, not
    # propagated into directory paths the operator later cannot find.
    with pytest.raises(InvalidRunId):
        RunArtifactLayout.from_run_id(
            agent_name="demo",
            run_id="not-a-run-id",
        )


def test_run_artifact_layout_paths_compose_consistently(
    tmp_path: Path,
) -> None:
    layout = RunArtifactLayout.from_run_id(
        agent_name="demo",
        run_id="20260425T173000Z",
        runs_root=tmp_path,
    )
    case_id = "smoke"
    assert layout.case_dir(case_id).parent == layout.run_dir
    assert (
        layout.dom_snapshot_dir(case_id)
        == layout.case_dir(case_id)
        / TRACE_SUBDIR
        / DOM_SNAPSHOTS_SUBDIR
    )
    assert layout.tool_call_log_path(case_id).name == (
        TOOL_CALL_LOG_FILENAME
    )
    assert (
        layout.routing_decision_log_path(case_id).name
        == ROUTING_DECISION_LOG_FILENAME
    )
    assert (
        layout.step_count_path(case_id).name
        == STEP_COUNT_FILENAME
    )
    assert (
        layout.generation_log_path(case_id).name
        == GENERATION_LOG_FILENAME
    )
    assert (
        layout.observability_log_dir(case_id)
        == layout.case_dir(case_id)
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
    )


def test_dom_snapshot_path_zero_pads_step_number(
    tmp_path: Path,
) -> None:
    # Three-digit zero-pad keeps lexical and numeric ordering
    # aligned. A regression that drops the pad would scramble
    # the post-submit-vs-landing ordering once step numbers
    # cross 9 or 99.
    layout = RunArtifactLayout.from_run_id(
        agent_name="demo",
        run_id="20260425T173000Z",
        runs_root=tmp_path,
    )
    path = layout.dom_snapshot_path("c", 7, "after_submit")
    assert (
        path.name
        == f"{EXPLICIT_DOM_PREFIX}-007-after_submit.html"
    )


def test_create_owner_only_dir_sets_0o700_on_new_path(
    tmp_path: Path,
) -> None:
    target = tmp_path / "case_dir"
    create_owner_only_dir(target)
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == OWNER_ONLY_MODE


def test_create_owner_only_dir_recurses_through_intermediate_dirs(
    tmp_path: Path,
) -> None:
    # Nested creation must lock down EVERY intermediate dir, not
    # just the leaf. A world-readable parent of an owner-only leaf
    # is a real exposure (the leaf's path is readable through it).
    target = tmp_path / "a" / "b" / "c"
    create_owner_only_dir(target)
    for path in (
        target,
        target.parent,
        target.parent.parent,
    ):
        assert (
            stat.S_IMODE(path.stat().st_mode)
            == OWNER_ONLY_MODE
        )


def test_create_owner_only_dir_chmods_existing_loose_permissions(
    tmp_path: Path,
) -> None:
    # If the dir already exists with looser permissions (prior run,
    # external setup), re-asserting 0o700 is mandatory — silently
    # honoring the existing mode would leave a permissive dir.
    target = tmp_path / "preexisting"
    target.mkdir(mode=0o755)
    target.chmod(0o755)
    create_owner_only_dir(target)
    assert (
        stat.S_IMODE(target.stat().st_mode)
        == OWNER_ONLY_MODE
    )


def test_create_owner_only_dir_restores_umask(
    tmp_path: Path,
) -> None:
    # The umask context manager mutates a process-global. A leak
    # would silently restrict every later mkdir in the test
    # process — guard against the regression by snapshotting the
    # mask before and after.
    prior = os.umask(0o022)
    try:
        create_owner_only_dir(tmp_path / "leaf")
        after = os.umask(prior)
        assert after == 0o022
    finally:
        os.umask(prior)
