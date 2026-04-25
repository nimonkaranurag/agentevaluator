"""
Unit tests for plan_swarm and the SwarmPlan / SwarmEntry / DriverInvocation schemas.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from evaluate_agent.manifest.schema import AgentManifest
from evaluate_agent.orchestration import (
    DriverInvocation,
    SwarmEntry,
    SwarmPlan,
    plan_swarm,
)
from pydantic import ValidationError


def _build_manifest(
    case_ids: tuple[str, ...] = ("case_alpha",),
    name: str = "demo-agent",
) -> AgentManifest:
    return AgentManifest.model_validate(
        {
            "name": name,
            "access": {"url": "https://example.com"},
            "cases": [
                {"id": case_id, "input": f"input-{case_id}"}
                for case_id in case_ids
            ],
        }
    )


def _frozen_now() -> datetime:
    return datetime(
        2026, 4, 25, 17, 30, 0, tzinfo=timezone.utc
    )


class TestPlanShape:
    def test_single_case_manifest_emits_one_entry(
        self,
        tmp_path: Path,
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        assert len(plan.entries) == 1
        assert plan.entries[0].case_id == "case_alpha"

    def test_entries_match_case_declaration_order(
        self,
        tmp_path: Path,
    ) -> None:
        case_ids = (
            "case_alpha",
            "case_beta",
            "case_gamma",
        )
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(case_ids),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        assert tuple(e.case_id for e in plan.entries) == (
            case_ids
        )

    def test_run_id_is_strftime_of_supplied_now(
        self,
        tmp_path: Path,
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        assert plan.run_id == "20260425T173000Z"

    def test_default_now_produces_well_formed_run_id(
        self,
        tmp_path: Path,
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
        )
        assert datetime.strptime(
            plan.run_id, "%Y%m%dT%H%M%SZ"
        )

    def test_agent_name_matches_manifest_name(
        self,
        tmp_path: Path,
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(name="some-other-agent"),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        assert plan.agent_name == "some-other-agent"

    def test_runs_root_is_resolved_to_absolute(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=Path("relative-runs"),
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        assert plan.runs_root.is_absolute()
        assert (
            plan.runs_root
            == (tmp_path / "relative-runs").resolve()
        )

    def test_manifest_path_is_resolved_to_absolute(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.yaml").write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            Path("agent.yaml"),
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        assert plan.manifest_path.is_absolute()
        assert (
            plan.manifest_path
            == (tmp_path / "agent.yaml").resolve()
        )

    def test_case_dir_lives_under_run_dir(
        self,
        tmp_path: Path,
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        runs_root = tmp_path / "runs"
        plan = plan_swarm(
            _build_manifest(("case_alpha",)),
            manifest_path,
            runs_root=runs_root,
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        entry = plan.entries[0]
        assert entry.case_dir == (
            runs_root.resolve()
            / "demo-agent"
            / "20260425T173000Z"
            / "case_alpha"
        )


class TestDriverInvocationContract:
    def _plan(self, tmp_path: Path) -> SwarmPlan:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        return plan_swarm(
            _build_manifest(("case_alpha", "case_beta")),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )

    def test_script_is_resolved_absolute_path(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        for entry in plan.entries:
            assert (
                entry.driver_invocation.script.is_absolute()
            )
            assert (
                entry.driver_invocation.script
                == (tmp_path / "open_agent.py").resolve()
            )

    def test_first_argument_is_absolute_manifest_path(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        for entry in plan.entries:
            assert entry.driver_invocation.arguments[
                0
            ] == str((tmp_path / "agent.yaml").resolve())

    def test_arguments_select_the_entry_case_via_case_flag(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        for entry in plan.entries:
            args = entry.driver_invocation.arguments
            case_index = args.index("--case")
            assert args[case_index + 1] == entry.case_id

    def test_arguments_set_submit_flag(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        for entry in plan.entries:
            assert (
                "--submit"
                in entry.driver_invocation.arguments
            )

    def test_arguments_pin_runs_root(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        for entry in plan.entries:
            args = entry.driver_invocation.arguments
            runs_root_index = args.index("--runs-root")
            assert args[runs_root_index + 1] == str(
                plan.runs_root
            )

    def test_arguments_pin_run_id_to_plan_run_id(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        for entry in plan.entries:
            args = entry.driver_invocation.arguments
            run_id_index = args.index("--run-id")
            assert args[run_id_index + 1] == plan.run_id

    def test_every_entry_pins_the_same_run_id(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        run_ids = {
            entry.driver_invocation.arguments[
                entry.driver_invocation.arguments.index(
                    "--run-id"
                )
                + 1
            ]
            for entry in plan.entries
        }
        assert run_ids == {plan.run_id}


class TestSchemaConstraints:
    def test_swarm_plan_is_frozen(
        self, tmp_path: Path
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        with pytest.raises(ValidationError):
            plan.run_id = "20990101T000000Z"

    def test_swarm_entry_is_frozen(
        self, tmp_path: Path
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        with pytest.raises(ValidationError):
            plan.entries[0].case_id = "other"

    def test_driver_invocation_is_frozen(
        self, tmp_path: Path
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        with pytest.raises(ValidationError):
            plan.entries[0].driver_invocation.script = Path(
                "/x"
            )

    def test_swarm_plan_rejects_extra_fields(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            SwarmPlan.model_validate(
                {
                    "run_id": "20260425T173000Z",
                    "agent_name": "demo",
                    "runs_root": "/tmp/r",
                    "manifest_path": "/tmp/a.yaml",
                    "entries": [
                        {
                            "case_id": "c",
                            "case_dir": "/tmp/r/demo/20260425T173000Z/c",
                            "driver_invocation": {
                                "script": "/tmp/o.py",
                                "arguments": ["a"],
                            },
                        }
                    ],
                    "extra_field": "not allowed",
                }
            )

    def test_swarm_entry_rejects_extra_fields(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            SwarmEntry.model_validate(
                {
                    "case_id": "c",
                    "case_dir": "/tmp/x",
                    "driver_invocation": {
                        "script": "/tmp/o.py",
                        "arguments": ["a"],
                    },
                    "extra": "nope",
                }
            )

    def test_driver_invocation_rejects_extra_fields(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            DriverInvocation.model_validate(
                {
                    "script": "/tmp/o.py",
                    "arguments": ["a"],
                    "extra": "nope",
                }
            )

    def test_swarm_plan_run_id_must_match_format(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            SwarmPlan.model_validate(
                {
                    "run_id": "not-a-run-id",
                    "agent_name": "demo",
                    "runs_root": "/tmp/r",
                    "manifest_path": "/tmp/a.yaml",
                    "entries": [
                        {
                            "case_id": "c",
                            "case_dir": "/tmp/r/demo/X/c",
                            "driver_invocation": {
                                "script": "/tmp/o.py",
                                "arguments": ["a"],
                            },
                        }
                    ],
                }
            )

    def test_swarm_plan_run_id_strict_calendar(
        self,
    ) -> None:
        # Feb 30 is regex-shaped but calendar-invalid.
        with pytest.raises(ValidationError):
            SwarmPlan.model_validate(
                {
                    "run_id": "20260230T000000Z",
                    "agent_name": "demo",
                    "runs_root": "/tmp/r",
                    "manifest_path": "/tmp/a.yaml",
                    "entries": [
                        {
                            "case_id": "c",
                            "case_dir": "/tmp/r/demo/X/c",
                            "driver_invocation": {
                                "script": "/tmp/o.py",
                                "arguments": ["a"],
                            },
                        }
                    ],
                }
            )

    def test_swarm_plan_requires_at_least_one_entry(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            SwarmPlan.model_validate(
                {
                    "run_id": "20260425T173000Z",
                    "agent_name": "demo",
                    "runs_root": "/tmp/r",
                    "manifest_path": "/tmp/a.yaml",
                    "entries": [],
                }
            )

    def test_driver_invocation_requires_at_least_one_argument(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            DriverInvocation.model_validate(
                {
                    "script": "/tmp/o.py",
                    "arguments": [],
                }
            )


class TestJSONRoundTrip:
    def _plan(self, tmp_path: Path) -> SwarmPlan:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        return plan_swarm(
            _build_manifest(
                ("case_alpha", "case_beta", "case_gamma")
            ),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )

    def test_dump_then_validate_returns_equal_plan(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        roundtripped = SwarmPlan.model_validate_json(
            plan.model_dump_json()
        )
        assert roundtripped == plan

    def test_dumped_json_contains_all_top_level_keys(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        payload: dict[str, Any] = json.loads(
            plan.model_dump_json()
        )
        assert set(payload.keys()) == {
            "run_id",
            "agent_name",
            "runs_root",
            "manifest_path",
            "entries",
        }

    def test_dumped_json_serializes_paths_as_strings(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        payload: dict[str, Any] = json.loads(
            plan.model_dump_json()
        )
        assert isinstance(payload["runs_root"], str)
        assert isinstance(payload["manifest_path"], str)
        for entry in payload["entries"]:
            assert isinstance(entry["case_dir"], str)
            assert isinstance(
                entry["driver_invocation"]["script"],
                str,
            )

    def test_dumped_entries_preserve_declaration_order(
        self, tmp_path: Path
    ) -> None:
        plan = self._plan(tmp_path)
        payload: dict[str, Any] = json.loads(
            plan.model_dump_json()
        )
        assert [
            entry["case_id"] for entry in payload["entries"]
        ] == ["case_alpha", "case_beta", "case_gamma"]


class TestDeterminism:
    def test_identical_inputs_produce_identical_plans(
        self, tmp_path: Path
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        first = plan_swarm(
            _build_manifest(("case_alpha", "case_beta")),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        second = plan_swarm(
            _build_manifest(("case_alpha", "case_beta")),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        assert first == second

    def test_different_now_produces_different_run_id(
        self, tmp_path: Path
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        first = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=_frozen_now(),
        )
        second = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            driver_script=tmp_path / "open_agent.py",
            now=datetime(
                2099,
                1,
                1,
                tzinfo=timezone.utc,
            ),
        )
        assert first.run_id != second.run_id


class TestDefaultDriverScript:
    def test_default_resolves_to_colocated_open_agent_py(
        self, tmp_path: Path
    ) -> None:
        manifest_path = tmp_path / "agent.yaml"
        manifest_path.write_text("placeholder")
        plan = plan_swarm(
            _build_manifest(),
            manifest_path,
            runs_root=tmp_path / "runs",
            now=_frozen_now(),
        )
        script = plan.entries[0].driver_invocation.script
        assert script.is_absolute()
        assert script.name == "open_agent.py"
        assert script.parent.name == "scripts"
        assert script.exists()
