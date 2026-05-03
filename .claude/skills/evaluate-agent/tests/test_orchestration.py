"""
Failure-mode tests for plan_swarm composition and CaseDirective contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from evaluate_agent.manifest.api_version import (
    CURRENT_API_VERSION,
)
from evaluate_agent.manifest.schema import AgentManifest
from evaluate_agent.orchestration import (
    CaseDirective,
    SwarmPlan,
    plan_swarm,
)
from evaluate_agent.orchestration.case_directive import (
    CaseDirective as DirectiveModel,
)
from pydantic import ValidationError

_FIXED_NOW = datetime(
    2026, 4, 25, 17, 30, 0, tzinfo=timezone.utc
)


def _two_case_manifest() -> AgentManifest:
    return AgentManifest.model_validate(
        {
            "apiVersion": CURRENT_API_VERSION,
            "name": "demo",
            "access": {"url": "https://example.com/chat"},
            "interaction": {
                "preconditions": [
                    {
                        "action": "click",
                        "selector": "button#a",
                    }
                ],
                "input_selector": "textarea",
                "response_wait_ms": 3000,
            },
            "cases": [
                {
                    "id": "first",
                    "input": "hello",
                    "assertions": {
                        "final_response_contains": "x"
                    },
                },
                {
                    "id": "second",
                    "input": "hi",
                    "assertions": {"must_call": ["lookup"]},
                },
            ],
        }
    )


def test_plan_swarm_emits_one_directive_per_manifest_case(
    tmp_path: Path,
) -> None:
    plan = plan_swarm(
        _two_case_manifest(),
        manifest_path=tmp_path / "agent.yaml",
        runs_root=tmp_path,
        now=_FIXED_NOW,
    )
    assert plan.run_id == "20260425T173000Z"
    assert [d.case_id for d in plan.directives] == [
        "first",
        "second",
    ]


def test_plan_swarm_paths_share_run_id(
    tmp_path: Path,
) -> None:
    # All directives in one plan must agree on the run_id
    # (they share artifacts in one run directory). A
    # regression that re-derived the run_id per directive
    # would scatter artifacts across directories.
    plan = plan_swarm(
        _two_case_manifest(),
        manifest_path=tmp_path / "agent.yaml",
        runs_root=tmp_path,
        now=_FIXED_NOW,
    )
    for directive in plan.directives:
        assert plan.run_id in str(directive.case_dir)


def test_plan_swarm_propagates_interaction_fields(
    tmp_path: Path,
) -> None:
    plan = plan_swarm(
        _two_case_manifest(),
        manifest_path=tmp_path / "agent.yaml",
        runs_root=tmp_path,
        now=_FIXED_NOW,
    )
    first = plan.directives[0]
    assert first.input_selector == "textarea"
    assert first.response_wait_ms == 3000
    assert len(first.preconditions) == 1


def test_plan_swarm_resolves_runs_root_to_absolute(
    tmp_path: Path,
) -> None:
    # Sub-agents launched via MCP cannot rely on the parent's
    # CWD; the directive must carry an absolute path.
    plan = plan_swarm(
        _two_case_manifest(),
        manifest_path=tmp_path / "agent.yaml",
        runs_root=tmp_path,
        now=_FIXED_NOW,
    )
    assert plan.runs_root.is_absolute()
    for directive in plan.directives:
        assert directive.case_dir.is_absolute()


def test_swarm_plan_run_id_validator_rejects_malformed() -> (
    None
):
    # The plan record itself enforces run_id format. A test
    # that constructs SwarmPlan directly (not through
    # plan_swarm) must still be rejected if the run_id is
    # malformed.
    with pytest.raises(ValidationError):
        SwarmPlan.model_validate(
            {
                "run_id": "bad",
                "agent_name": "demo",
                "runs_root": "/tmp/runs",
                "manifest_path": "/tmp/agent.yaml",
                "directives": [],
            }
        )


def test_case_directive_response_wait_ms_upper_bound() -> (
    None
):
    # Manifest schema caps at 120000ms. The directive mirror
    # has the same cap so a hand-constructed plan can't
    # bypass the manifest's bounds.
    with pytest.raises(ValidationError):
        DirectiveModel.model_validate(
            {
                "case_id": "c",
                "case_dir": "/tmp/c",
                "url": "https://example.com",
                "case_input": "hi",
                "response_wait_ms": 200_000,
                "landing_screenshot_path": "/tmp/a.png",
                "landing_dom_snapshot_path": "/tmp/a.html",
                "after_submit_screenshot_path": "/tmp/b.png",
                "after_submit_dom_snapshot_path": (
                    "/tmp/b.html"
                ),
                "tool_call_log_path": (
                    "/tmp/tool_calls.jsonl"
                ),
                "routing_decision_log_path": (
                    "/tmp/routing.jsonl"
                ),
                "step_count_path": "/tmp/step_count.json",
                "generation_log_path": (
                    "/tmp/generations.jsonl"
                ),
            }
        )
