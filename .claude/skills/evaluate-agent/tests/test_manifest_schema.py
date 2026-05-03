"""
Failure-mode tests for the manifest schema's cross-field and per-field validators.
"""

from __future__ import annotations

from typing import Any

import pytest
from evaluate_agent.manifest.api_version import (
    CURRENT_API_VERSION,
)
from evaluate_agent.manifest.schema import (
    AgentManifest,
    Assertions,
    Case,
    Precondition,
)
from pydantic import ValidationError


def _minimal_manifest_dict(
    **overrides: Any,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "apiVersion": CURRENT_API_VERSION,
        "name": "demo-agent",
        "access": {"url": "https://example.com/chat"},
        "cases": [
            {
                "id": "smoke",
                "input": "hello",
                "assertions": {
                    "final_response_contains": "world"
                },
            }
        ],
    }
    base.update(overrides)
    return base


def test_precondition_select_requires_value() -> None:
    with pytest.raises(ValidationError) as info:
        Precondition(action="select", selector="#x")
    assert "requires value to be set" in str(info.value)


def test_precondition_fill_requires_value() -> None:
    with pytest.raises(ValidationError):
        Precondition(action="fill", selector="textarea")


def test_precondition_click_rejects_value() -> None:
    # value-on-click is a category error: clicks have no payload,
    # and silently dropping it would mask a misconfigured manifest.
    with pytest.raises(ValidationError) as info:
        Precondition(
            action="click", selector="button", value="x"
        )
    assert "must not declare value" in str(info.value)


def test_assertions_must_call_and_must_not_call_disjoint() -> (
    None
):
    with pytest.raises(ValidationError) as info:
        Assertions(
            must_call=["lookup", "send"],
            must_not_call=["lookup"],
        )
    assert "overlap" in str(info.value)
    assert "lookup" in str(info.value)


def test_assertions_must_call_exactly_rejects_zero() -> (
    None
):
    # Use must_not_call to forbid; must_call_exactly=0 is the wrong
    # tool for that job and the validator should redirect.
    with pytest.raises(ValidationError) as info:
        Assertions(must_call_exactly={"lookup": 0})
    assert "must be >= 1" in str(info.value).replace(
        "\n", " "
    ) or ">=" in str(info.value)


def test_case_requires_at_least_one_assertion() -> None:
    # A case with empty assertions would silently pass scoring —
    # the schema must reject it at load time so the operator can
    # tell the difference between "passing" and "vacuously passing".
    with pytest.raises(ValidationError) as info:
        Case(
            id="empty", input="hi", assertions=Assertions()
        )
    assert "no checks" in str(info.value)


def test_manifest_rejects_duplicate_case_ids() -> None:
    payload = _minimal_manifest_dict(
        cases=[
            {
                "id": "dup",
                "input": "a",
                "assertions": {
                    "final_response_contains": "x"
                },
            },
            {
                "id": "dup",
                "input": "b",
                "assertions": {
                    "final_response_contains": "y"
                },
            },
        ]
    )
    with pytest.raises(ValidationError) as info:
        AgentManifest.model_validate(payload)
    assert "duplicate case ids" in str(info.value)


def test_manifest_requires_at_least_one_case() -> None:
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(
            _minimal_manifest_dict(cases=[])
        )


def test_manifest_tools_catalog_cross_validates_must_call() -> (
    None
):
    payload = _minimal_manifest_dict(
        tools_catalog=["lookup"],
        cases=[
            {
                "id": "c",
                "input": "hi",
                "assertions": {"must_call": ["typo"]},
            }
        ],
    )
    with pytest.raises(ValidationError) as info:
        AgentManifest.model_validate(payload)
    detail = str(info.value)
    assert "undeclared tool" in detail
    assert "typo" in detail


def test_manifest_tools_catalog_cross_validates_must_call_with_args() -> (
    None
):
    # CallSpec.tool_name reuses the same catalog gate as must_call;
    # a typo here would surface only at runtime when the tool was
    # never seen — fail fast at load time instead.
    payload = _minimal_manifest_dict(
        tools_catalog=["transfer_funds"],
        cases=[
            {
                "id": "c",
                "input": "hi",
                "assertions": {
                    "must_call_with_args": [
                        {
                            "tool_name": "transfer_typo",
                            "args": {"amount": 100},
                        }
                    ]
                },
            }
        ],
    )
    with pytest.raises(ValidationError) as info:
        AgentManifest.model_validate(payload)
    assert "transfer_typo" in str(info.value)


def test_manifest_agents_catalog_cross_validates_must_route_to() -> (
    None
):
    payload = _minimal_manifest_dict(
        agents_catalog=["billing"],
        cases=[
            {
                "id": "c",
                "input": "hi",
                "assertions": {
                    "must_route_to": "support_typo"
                },
            }
        ],
    )
    with pytest.raises(ValidationError) as info:
        AgentManifest.model_validate(payload)
    assert "support_typo" in str(info.value)


def test_manifest_rejects_unknown_top_level_key() -> None:
    # extra="forbid" on StrictFrozen is the contract — typos in
    # field names would otherwise be silently dropped, producing
    # a manifest that loads but does the wrong thing.
    payload = _minimal_manifest_dict(unexpected_key="oops")
    with pytest.raises(ValidationError) as info:
        AgentManifest.model_validate(payload)
    assert "unexpected_key" in str(info.value)


def test_manifest_response_wait_ms_lower_bound() -> None:
    # Below 100ms the post-submit DOM is captured before any real
    # agent has rendered its first byte; the lower bound exists
    # to prevent a false-fail on every case.
    payload = _minimal_manifest_dict(
        interaction={"response_wait_ms": 50}
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_response_wait_ms_upper_bound() -> None:
    payload = _minimal_manifest_dict(
        interaction={"response_wait_ms": 200_000}
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_max_dom_bytes_lower_bound() -> None:
    # 64 KiB is the documented floor; smaller caps would reject
    # legitimate small-page chat UIs and yield false inconclusive.
    payload = _minimal_manifest_dict(
        interaction={"max_dom_bytes": 1024}
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_rejects_disallowed_url_scheme() -> None:
    # WebAccess._scheme_is_allowlisted is the defense-in-depth
    # check on top of HttpUrl. Even if a future Pydantic relaxed
    # HttpUrl, this guard rejects file://.
    payload = _minimal_manifest_dict(
        access={"url": "ftp://example.com"}
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_langfuse_default_host_policy_rejects_http() -> (
    None
):
    # Default policy is https_only. A plaintext localhost host
    # without an explicit policy must FAIL — silently allowing it
    # would regress production manifests authored to the loopback
    # dev pattern.
    payload = _minimal_manifest_dict(
        observability={
            "langfuse": {"host": "http://localhost:3010"}
        }
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_langfuse_loopback_policy_accepts_localhost() -> (
    None
):
    payload = _minimal_manifest_dict(
        observability={
            "langfuse": {
                "host": "http://localhost:3010",
                "host_policy": "insecure_loopback_only",
            }
        }
    )
    AgentManifest.model_validate(payload)


def test_manifest_otel_loopback_policy_rejects_public_host() -> (
    None
):
    payload = _minimal_manifest_dict(
        observability={
            "otel": {
                "endpoint": "http://collector.example.com",
                "host_policy": "insecure_loopback_only",
            }
        }
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_max_total_cost_must_be_positive() -> None:
    # Float field uses gt=0 — a $0 budget makes no sense and
    # would resolve to inconclusive against any non-empty trace.
    payload = _minimal_manifest_dict(
        cases=[
            {
                "id": "c",
                "input": "hi",
                "assertions": {"max_total_cost_usd": 0.0},
            }
        ]
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_ui_introspection_requires_at_least_one_kind() -> (
    None
):
    # exposes is min_length=1 — declaring ui_introspection with
    # an empty exposes is a misconfiguration the loader catches.
    payload = _minimal_manifest_dict(
        observability={
            "ui_introspection": {
                "description": "panel description",
                "exposes": [],
            }
        }
    )
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(payload)


def test_manifest_accepts_full_well_formed_payload() -> (
    None
):
    # One canonical happy path — confirms the schema accepts a
    # manifest exercising every optional block we care about.
    payload = _minimal_manifest_dict(
        description="a one-line description",
        observability={
            "langfuse": {
                "host": "https://cloud.langfuse.com",
                "public_key_env": "LANGFUSE_PUBLIC_KEY",
                "secret_key_env": "LANGFUSE_SECRET_KEY",
            },
            "ui_introspection": {
                "description": "reasoning panel",
                "reveal_actions": [
                    {
                        "action": "click",
                        "selector": (
                            "button[aria-label='Show reasoning']"
                        ),
                    }
                ],
                "exposes": ["tool_calls"],
            },
        },
        interaction={
            "preconditions": [
                {
                    "action": "select",
                    "selector": "#agent",
                    "value": "demo",
                }
            ],
            "input_selector": "[contenteditable='true']",
            "response_wait_ms": 5000,
        },
        tools_catalog=["lookup", "send"],
        cases=[
            {
                "id": "c1",
                "input": "hi",
                "assertions": {
                    "must_call": ["lookup"],
                    "must_not_call": ["send"],
                    "must_call_exactly": {"lookup": 1},
                    "must_call_with_args": [
                        {
                            "tool_name": "lookup",
                            "args": {"alias": "alex"},
                            "min_count": 1,
                        }
                    ],
                    "must_call_in_order": ["lookup"],
                    "max_steps": 4,
                    "final_response_contains": "ok",
                    "max_total_tokens": 1000,
                    "max_total_cost_usd": 0.05,
                    "max_latency_ms": 8000,
                },
            }
        ],
    )
    manifest = AgentManifest.model_validate(payload)
    assert manifest.name == "demo-agent"
    assert len(manifest.cases) == 1
    assert manifest.cases[0].assertions.max_steps == 4
