"""
Failure-mode tests for the observability_fetchers package: credentials, writer, normalizers, shared transforms.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from evaluate_agent.common.errors.observability_fetchers import (
    LangfuseCredentialEnvVarMissing,
    OtelHeadersEnvMissing,
    OtelHeadersMalformed,
)
from evaluate_agent.manifest.schema import (
    LangfuseSource,
    OtelSource,
)
from evaluate_agent.observability_fetchers import (
    LANGFUSE_AGENT_TYPE,
    LANGFUSE_GENERATION_TYPE,
    LANGFUSE_TOOL_TYPE,
    NormalizedSpan,
    SpanKind,
    normalize_langfuse_observations,
    normalize_otel_resource_spans,
    observability_log_dir_for,
    resolve_langfuse_credentials,
    resolve_otel_credentials,
    write_observability_artifacts,
)
from evaluate_agent.observability_fetchers.common.transforms import (
    generations_from_normalized_spans,
    routing_decisions_from_normalized_spans,
    step_count_from_normalized_spans,
    tool_calls_from_normalized_spans,
)
from evaluate_agent.observability_fetchers.otel import (
    ATTR_AGENT_NAME,
    ATTR_OPERATION_NAME,
    ATTR_REQUEST_MODEL,
    ATTR_TOOL_NAME,
    ATTR_TOOL_PARAMETERS,
    ATTR_USAGE_INPUT_COST_USD,
    ATTR_USAGE_INPUT_TOKENS,
    ATTR_USAGE_OUTPUT_COST_USD,
    ATTR_USAGE_OUTPUT_TOKENS,
    OPERATION_EXECUTE_TOOL,
    OPERATION_INVOKE_AGENT,
    classify_otel_span,
)
from evaluate_agent.scoring.observability.schema import (
    StepCount,
    ToolCall,
)

# ---------- LangFuse credentials ----------


def _langfuse_source(
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
        _langfuse_source("https://host.example.com/")
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
        resolve_langfuse_credentials(_langfuse_source())
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
        resolve_langfuse_credentials(_langfuse_source())


# ---------- OTEL credentials ----------


def _otel_source(
    *,
    endpoint: str = "https://otel.example.com",
    headers_env: str | None = None,
) -> OtelSource:
    payload: dict[str, object] = {"endpoint": endpoint}
    if headers_env is not None:
        payload["headers_env"] = headers_env
    return OtelSource.model_validate(payload)


def test_resolve_otel_credentials_strips_trailing_slash() -> (
    None
):
    creds = resolve_otel_credentials(
        _otel_source(endpoint="https://otel.example.com/")
    )
    assert creds.endpoint == "https://otel.example.com"
    assert creds.headers == {}


def test_resolve_otel_credentials_parses_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_HEADERS",
        "Authorization=Bearer abc,X-Tenant=acme",
    )
    creds = resolve_otel_credentials(
        _otel_source(
            headers_env="OTEL_EXPORTER_OTLP_HEADERS"
        )
    )
    assert creds.headers == {
        "Authorization": "Bearer abc",
        "X-Tenant": "acme",
    }


def test_resolve_otel_credentials_raises_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "OTEL_EXPORTER_OTLP_HEADERS", raising=False
    )
    with pytest.raises(OtelHeadersEnvMissing) as info:
        resolve_otel_credentials(
            _otel_source(
                headers_env="OTEL_EXPORTER_OTLP_HEADERS"
            )
        )
    assert (
        info.value.env_var == "OTEL_EXPORTER_OTLP_HEADERS"
    )


def test_resolve_otel_credentials_rejects_pair_without_equals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A header pair lacking the `=` separator is
    # indistinguishable from a value-less key and would
    # silently produce an empty header. Reject explicitly so
    # the OTLP backend doesn't see a malformed Authorization
    # header at query time.
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_HEADERS",
        "Authorization Bearer abc",
    )
    with pytest.raises(OtelHeadersMalformed) as info:
        resolve_otel_credentials(
            _otel_source(
                headers_env="OTEL_EXPORTER_OTLP_HEADERS"
            )
        )
    assert (
        info.value.offending_pair
        == "Authorization Bearer abc"
    )


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


# ---------- LangFuse normalize + shared transforms ----------


def _to_tool_calls(observations):
    return tool_calls_from_normalized_spans(
        normalize_langfuse_observations(observations)
    )


def _to_routing_decisions(observations):
    return routing_decisions_from_normalized_spans(
        normalize_langfuse_observations(observations)
    )


def _to_step_count(observations):
    return step_count_from_normalized_spans(
        normalize_langfuse_observations(observations)
    )


def _to_generations(observations):
    return generations_from_normalized_spans(
        normalize_langfuse_observations(observations)
    )


def test_langfuse_tool_calls_filter_by_kind() -> None:
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
    out = _to_tool_calls(observations)
    assert len(out) == 1
    assert out[0].tool_name == "lookup"
    assert out[0].arguments == {"alias": "alex"}


def test_langfuse_tool_calls_skip_observations_missing_id() -> (
    None
):
    # An observation lacking an id can't anchor a citation.
    # Skipping (rather than raising) lets us tolerate partial
    # fetcher output without aborting the whole case.
    observations = [
        {"type": LANGFUSE_TOOL_TYPE, "name": "lookup"},
        {
            "type": LANGFUSE_TOOL_TYPE,
            "id": "t2",
            "name": "send",
        },
    ]
    out = _to_tool_calls(observations)
    assert [c.tool_name for c in out] == ["send"]


def test_langfuse_routing_decisions_resolve_from_agent() -> (
    None
):
    # The renderer wants both the parent agent (who routed)
    # and the target (who received). Resolving from_agent via
    # the parent_observation_id lookup is the documented
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
    out = _to_routing_decisions(observations)
    target = next(d for d in out if d.span_id == "a2")
    assert target.from_agent == "supervisor"


def test_langfuse_step_count_walks_top_level_only() -> None:
    # Step semantics: an AGENT/TOOL whose direct parent is
    # the trace root or another AGENT counts as a step.
    # Nested TOOL-under-TOOL retries do NOT.
    observations = [
        {
            "type": LANGFUSE_AGENT_TYPE,
            "id": "a1",
            "name": "supervisor",
            "start_time": "2026-04-25T17:30:00Z",
        },
        {
            "type": LANGFUSE_TOOL_TYPE,
            "id": "t1",
            "name": "lookup",
            "parent_observation_id": "a1",
            "start_time": "2026-04-25T17:30:01Z",
        },
        {
            "type": LANGFUSE_TOOL_TYPE,
            "id": "t1_retry",
            "name": "lookup_retry",
            "parent_observation_id": "t1",
            "start_time": "2026-04-25T17:30:02Z",
        },
    ]
    record = _to_step_count(observations)
    assert record.total_steps == 2
    assert record.step_span_ids == ("a1", "t1")


def test_langfuse_step_count_orders_by_start_time() -> None:
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
    record = _to_step_count(observations)
    assert record.step_span_ids == ("first", "second")


def test_langfuse_generations_extract_usage_and_cost() -> (
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
    out = _to_generations(observations)
    assert len(out) == 1
    g = out[0]
    assert g.total_tokens == 120
    assert g.total_cost_usd == 0.004
    assert g.started_at == "2026-04-25T17:30:00Z"


def test_langfuse_generations_reject_negative_usage() -> (
    None
):
    # A buggy provider that emits negative usage values must
    # not silently inflate the generation record. Coercion
    # drops the value rather than passing it through.
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
    out = _to_generations(observations)
    assert out[0].input_tokens is None
    assert out[0].output_tokens == 10


def test_langfuse_generations_pass_datetime_through_iso() -> (
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
    out = _to_generations(observations)
    assert out[0].started_at == (
        "2026-04-25T17:30:00+00:00"
    )


# ---------- OTEL classifier ----------


def test_otel_classify_routes_tool_via_operation() -> None:
    attributes = {
        ATTR_OPERATION_NAME: OPERATION_EXECUTE_TOOL,
    }
    assert classify_otel_span(attributes) is SpanKind.TOOL


def test_otel_classify_routes_agent_via_operation() -> None:
    attributes = {
        ATTR_OPERATION_NAME: OPERATION_INVOKE_AGENT,
    }
    assert classify_otel_span(attributes) is SpanKind.AGENT


def test_otel_classify_routes_generation_via_usage_attribute() -> (
    None
):
    # An emitter that omits gen_ai.operation.name but stamps
    # token usage should still be recognised as a GENERATION,
    # otherwise the four token / cost / latency assertions
    # would silently resolve to inconclusive.
    attributes = {ATTR_USAGE_INPUT_TOKENS: 50}
    assert (
        classify_otel_span(attributes)
        is SpanKind.GENERATION
    )


def test_otel_classify_falls_back_to_other() -> None:
    assert (
        classify_otel_span({"unrelated.attr": 1})
        is SpanKind.OTHER
    )


# ---------- OTEL normalize ----------


def _otel_resource_spans(*spans: dict) -> list[dict]:
    return [
        {
            "resource": {"attributes": []},
            "scopeSpans": [
                {
                    "scope": {"name": "agent.tracer"},
                    "spans": list(spans),
                }
            ],
        }
    ]


def _otel_attribute(key: str, value: object) -> dict:
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {
            "key": key,
            "value": {"intValue": str(value)},
        }
    if isinstance(value, float):
        return {
            "key": key,
            "value": {"doubleValue": value},
        }
    return {
        "key": key,
        "value": {"stringValue": str(value)},
    }


def test_otel_normalize_skips_spans_without_span_id() -> (
    None
):
    spans = _otel_resource_spans(
        {
            "name": "anonymous",
            "attributes": [],
        },
        {
            "spanId": "abc",
            "name": "named",
            "attributes": [
                _otel_attribute(
                    ATTR_OPERATION_NAME,
                    OPERATION_EXECUTE_TOOL,
                ),
                _otel_attribute(ATTR_TOOL_NAME, "lookup"),
            ],
        },
    )
    out = normalize_otel_resource_spans(spans)
    assert [s.span_id for s in out] == ["abc"]


def test_otel_normalize_extracts_tool_name_and_parameters_from_attributes() -> (
    None
):
    spans = _otel_resource_spans(
        {
            "spanId": "t1",
            "name": "execute_tool people_directory.lookup",
            "startTimeUnixNano": "1714065000000000000",
            "endTimeUnixNano": "1714065001000000000",
            "attributes": [
                _otel_attribute(
                    ATTR_OPERATION_NAME,
                    OPERATION_EXECUTE_TOOL,
                ),
                _otel_attribute(ATTR_TOOL_NAME, "lookup"),
                _otel_attribute(
                    ATTR_TOOL_PARAMETERS,
                    json.dumps({"alias": "alex"}),
                ),
            ],
        }
    )
    [normalized] = normalize_otel_resource_spans(spans)
    assert normalized.kind is SpanKind.TOOL
    assert normalized.name == "lookup"
    assert normalized.input == {"alias": "alex"}
    # The unix-nano start time is converted to UTC ISO so the
    # canonical Generation / ToolCall records carry the same
    # string representation as LangFuse traces would.
    assert normalized.start_time is not None
    assert normalized.start_time.endswith("+00:00")


def test_otel_normalize_derives_total_tokens_when_only_halves_present() -> (
    None
):
    # GenAI semconv leaves `total` optional; the normalizer
    # derives it from input + output so max_total_tokens can
    # resolve against agents that only emit per-direction
    # counts.
    spans = _otel_resource_spans(
        {
            "spanId": "g1",
            "name": "chat",
            "attributes": [
                _otel_attribute(
                    ATTR_OPERATION_NAME, "chat"
                ),
                _otel_attribute(
                    ATTR_REQUEST_MODEL, "claude-x"
                ),
                _otel_attribute(
                    ATTR_USAGE_INPUT_TOKENS, 50
                ),
                _otel_attribute(
                    ATTR_USAGE_OUTPUT_TOKENS, 70
                ),
                _otel_attribute(
                    ATTR_USAGE_INPUT_COST_USD, 0.001
                ),
                _otel_attribute(
                    ATTR_USAGE_OUTPUT_COST_USD, 0.003
                ),
            ],
        }
    )
    [normalized] = normalize_otel_resource_spans(spans)
    assert normalized.kind is SpanKind.GENERATION
    assert normalized.total_tokens == 120
    assert normalized.input_tokens == 50
    assert normalized.output_tokens == 70


def test_otel_normalize_routes_agent_via_attribute_alone() -> (
    None
):
    # An emitter that uses gen_ai.agent.name without setting
    # gen_ai.operation.name should still classify as AGENT and
    # surface as a routing decision.
    spans = _otel_resource_spans(
        {
            "spanId": "a1",
            "name": "supervisor",
            "attributes": [
                _otel_attribute(
                    ATTR_AGENT_NAME, "supervisor"
                ),
            ],
        },
        {
            "spanId": "a2",
            "name": "billing",
            "parentSpanId": "a1",
            "attributes": [
                _otel_attribute(ATTR_AGENT_NAME, "billing"),
            ],
        },
    )
    out = routing_decisions_from_normalized_spans(
        normalize_otel_resource_spans(spans)
    )
    target = next(d for d in out if d.span_id == "a2")
    assert target.from_agent == "supervisor"


# ---------- Cross-source: shared transforms over hand-built spans ----------


def test_shared_transforms_route_by_kind_only() -> None:
    # A regression here would mean the source-agnostic
    # transforms are inadvertently coupling on a source-
    # specific field. Building NormalizedSpans directly (no
    # langfuse / otel involvement) catches that.
    spans = (
        NormalizedSpan(
            span_id="t1",
            parent_span_id=None,
            name="lookup",
            kind=SpanKind.TOOL,
            start_time="2026-04-25T17:30:00Z",
            end_time=None,
            input={"alias": "alex"},
            output="found",
        ),
        NormalizedSpan(
            span_id="a1",
            parent_span_id=None,
            name="supervisor",
            kind=SpanKind.AGENT,
            start_time="2026-04-25T17:30:00Z",
            end_time=None,
        ),
    )
    tool_calls = tool_calls_from_normalized_spans(spans)
    routing = routing_decisions_from_normalized_spans(spans)
    assert [c.tool_name for c in tool_calls] == ["lookup"]
    assert [d.target_agent for d in routing] == [
        "supervisor"
    ]
