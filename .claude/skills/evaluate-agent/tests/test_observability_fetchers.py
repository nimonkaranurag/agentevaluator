"""
Failure-mode tests for the observability_fetchers package: credentials, writer, and LangFuse transforms.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from evaluate_agent.common.errors.observability_fetchers import (
    LangfuseCredentialEnvVarMissing,
)
from evaluate_agent.manifest.schema import LangfuseSource
from evaluate_agent.observability_fetchers import (
    LANGFUSE_AGENT_TYPE,
    LANGFUSE_GENERATION_TYPE,
    LANGFUSE_TOOL_TYPE,
    observability_log_dir_for,
    resolve_langfuse_credentials,
    transform_observations_to_generations,
    transform_observations_to_routing_decisions,
    transform_observations_to_step_count,
    transform_observations_to_tool_calls,
    write_observability_artifacts,
)
from evaluate_agent.scoring.observability.schema import (
    Generation,
    RoutingDecision,
    StepCount,
    ToolCall,
)

# ---------- credentials ----------


def _source(
    host: str = "https://cloud.langfuse.com",
) -> LangfuseSource:
    return LangfuseSource.model_validate(
        {
            "host": host,
            "public_key_env": "LANGFUSE_PUBLIC_KEY",
            "secret_key_env": "LANGFUSE_SECRET_KEY",
        }
    )


def test_resolve_credentials_strips_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The host stored on credentials is concatenated with API
    # paths; a trailing slash would produce '//api/...' which
    # some servers route differently. Strip once at resolve time.
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    creds = resolve_langfuse_credentials(
        _source("https://host.example.com/")
    )
    assert creds.host == "https://host.example.com"


def test_resolve_credentials_raises_when_public_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    with pytest.raises(
        LangfuseCredentialEnvVarMissing
    ) as info:
        resolve_langfuse_credentials(_source())
    assert info.value.env_var == "LANGFUSE_PUBLIC_KEY"
    assert info.value.role == "public key"


def test_resolve_credentials_raises_when_value_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Empty-string credentials are indistinguishable from
    # unset to LangFuse — surface the same actionable error
    # rather than letting the SDK return a 401.
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    with pytest.raises(LangfuseCredentialEnvVarMissing):
        resolve_langfuse_credentials(_source())


# ---------- writer ----------


def test_writer_emits_jsonl_for_each_log(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "agent" / "20260425T173000Z" / "c"
    written = write_observability_artifacts(
        case_dir=case_dir,
        tool_calls=(
            ToolCall(tool_name="lookup", span_id="s1"),
        ),
        routing_decisions=(),
        step_count=StepCount(
            total_steps=1, step_span_ids=("s1",)
        ),
        generations=(),
    )
    assert written.tool_calls_path.is_file()
    body = written.tool_calls_path.read_text()
    assert body.endswith("\n")
    parsed = json.loads(body.splitlines()[0])
    assert parsed["tool_name"] == "lookup"


def test_writer_emits_empty_file_for_empty_log(
    tmp_path: Path,
) -> None:
    # Empty JSONL must still exist on disk so the resolver
    # distinguishes "no events captured" (empty file) from
    # "evidence missing" (no file). The test asserts both
    # the file exists and the body is empty.
    case_dir = tmp_path / "agent" / "20260425T173000Z" / "c"
    written = write_observability_artifacts(
        case_dir=case_dir,
        tool_calls=(),
        routing_decisions=(),
        step_count=StepCount(
            total_steps=0, step_span_ids=()
        ),
        generations=(),
    )
    assert written.tool_calls_path.is_file()
    assert written.tool_calls_path.read_text() == ""


def test_writer_writes_step_count_as_single_json_document(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "agent" / "20260425T173000Z" / "c"
    written = write_observability_artifacts(
        case_dir=case_dir,
        tool_calls=(),
        routing_decisions=(),
        step_count=StepCount(
            total_steps=2,
            step_span_ids=("s1", "s2"),
        ),
        generations=(),
    )
    payload = json.loads(
        written.step_count_path.read_text()
    )
    assert payload["total_steps"] == 2
    assert payload["step_span_ids"] == ["s1", "s2"]


def test_writer_lands_under_observability_log_dir(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "agent" / "20260425T173000Z" / "c"
    written = write_observability_artifacts(
        case_dir=case_dir,
        tool_calls=(),
        routing_decisions=(),
        step_count=StepCount(
            total_steps=0, step_span_ids=()
        ),
        generations=(),
    )
    expected_dir = observability_log_dir_for(case_dir)
    for path in (
        written.tool_calls_path,
        written.routing_decisions_path,
        written.step_count_path,
        written.generations_path,
    ):
        assert path.parent == expected_dir


# ---------- transforms ----------


def test_transform_tool_calls_filters_by_type() -> None:
    observations = [
        {
            "type": LANGFUSE_TOOL_TYPE,
            "id": "t1",
            "name": "lookup",
            "input": {"alias": "alex"},
        },
        {
            "type": LANGFUSE_AGENT_TYPE,
            "id": "a1",
            "name": "billing",
        },
    ]
    out = transform_observations_to_tool_calls(observations)
    assert len(out) == 1
    assert out[0].tool_name == "lookup"
    assert out[0].arguments == {"alias": "alex"}


def test_transform_tool_calls_skips_observations_missing_id() -> (
    None
):
    # An observation lacking an id can't anchor a citation.
    # Treating it as skipped (rather than raising) lets us
    # tolerate partial fetcher output without aborting the
    # whole case.
    observations = [
        {
            "type": LANGFUSE_TOOL_TYPE,
            "name": "lookup",
        },
        {
            "type": LANGFUSE_TOOL_TYPE,
            "id": "t2",
            "name": "send",
        },
    ]
    out = transform_observations_to_tool_calls(observations)
    assert [c.tool_name for c in out] == ["send"]


def test_transform_routing_decisions_resolves_from_agent() -> (
    None
):
    # The renderer wants both the parent agent (who routed)
    # and the target (who received). Resolving from_agent
    # via the parent_observation_id lookup is the documented
    # contract.
    observations = [
        {
            "type": LANGFUSE_AGENT_TYPE,
            "id": "a1",
            "name": "supervisor",
        },
        {
            "type": LANGFUSE_AGENT_TYPE,
            "id": "a2",
            "name": "billing",
            "parent_observation_id": "a1",
        },
    ]
    out = transform_observations_to_routing_decisions(
        observations
    )
    target = next(d for d in out if d.span_id == "a2")
    assert target.from_agent == "supervisor"


def test_transform_step_count_walks_top_level_only() -> (
    None
):
    # Step semantics: an AGENT/TOOL whose direct parent is
    # the trace root or another AGENT counts as a step.
    # Nested TOOL-under-TOOL retries do NOT. This is the
    # property that distinguishes user-perceived reasoning
    # steps from raw span counts.
    observations = [
        # Direct under root — step.
        {
            "type": LANGFUSE_AGENT_TYPE,
            "id": "a1",
            "name": "supervisor",
            "start_time": "2026-04-25T17:30:00Z",
        },
        # Direct under a1 (an AGENT) — step.
        {
            "type": LANGFUSE_TOOL_TYPE,
            "id": "t1",
            "name": "lookup",
            "parent_observation_id": "a1",
            "start_time": "2026-04-25T17:30:01Z",
        },
        # Under t1 (a TOOL) — NOT a step.
        {
            "type": LANGFUSE_TOOL_TYPE,
            "id": "t1_retry",
            "name": "lookup_retry",
            "parent_observation_id": "t1",
            "start_time": "2026-04-25T17:30:02Z",
        },
    ]
    record = transform_observations_to_step_count(
        observations
    )
    assert record.total_steps == 2
    assert record.step_span_ids == ("a1", "t1")


def test_transform_step_count_orders_by_start_time() -> (
    None
):
    # The ordering anchors the step list to the operator's
    # mental timeline. A regression that fell back to insertion
    # order would surface a wrong sequence in the report.
    observations = [
        {
            "type": LANGFUSE_AGENT_TYPE,
            "id": "second",
            "start_time": "2026-04-25T17:30:05Z",
        },
        {
            "type": LANGFUSE_AGENT_TYPE,
            "id": "first",
            "start_time": "2026-04-25T17:30:01Z",
        },
    ]
    record = transform_observations_to_step_count(
        observations
    )
    assert record.step_span_ids == ("first", "second")


def test_transform_generations_extracts_usage_and_cost() -> (
    None
):
    observations = [
        {
            "type": LANGFUSE_GENERATION_TYPE,
            "id": "g1",
            "model": "claude-x",
            "usage": {
                "input": 50,
                "output": 70,
                "total": 120,
            },
            "cost_details": {
                "input": 0.001,
                "output": 0.003,
                "total": 0.004,
            },
            "start_time": "2026-04-25T17:30:00Z",
            "end_time": "2026-04-25T17:30:01Z",
        }
    ]
    out = transform_observations_to_generations(
        observations
    )
    assert len(out) == 1
    g = out[0]
    assert g.total_tokens == 120
    assert g.total_cost_usd == 0.004
    assert g.started_at == "2026-04-25T17:30:00Z"


def test_transform_generations_rejects_negative_usage() -> (
    None
):
    # A buggy provider that emits negative usage values must
    # not silently inflate the generation record. The
    # _non_negative_*_or_none helpers drop the value rather
    # than passing it through unchanged.
    observations = [
        {
            "type": LANGFUSE_GENERATION_TYPE,
            "id": "g1",
            "usage": {
                "input": -1,
                "output": 10,
                "total": 9,
            },
        }
    ]
    out = transform_observations_to_generations(
        observations
    )
    assert out[0].input_tokens is None
    assert out[0].output_tokens == 10


def test_transform_generations_passes_datetime_through_iso() -> (
    None
):
    observations = [
        {
            "type": LANGFUSE_GENERATION_TYPE,
            "id": "g1",
            "start_time": datetime(
                2026, 4, 25, 17, 30, tzinfo=timezone.utc
            ),
        }
    ]
    out = transform_observations_to_generations(
        observations
    )
    assert out[0].started_at == (
        "2026-04-25T17:30:00+00:00"
    )
