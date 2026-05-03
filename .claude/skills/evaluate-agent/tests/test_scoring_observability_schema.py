"""
Failure-mode tests for the on-disk schemas the resolvers parse (ToolCall, RoutingDecision, StepCount, Generation).
"""

from __future__ import annotations

import pytest
from evaluate_agent.scoring.observability.schema import (
    Generation,
    RoutingDecision,
    StepCount,
    ToolCall,
)
from pydantic import ValidationError


def test_tool_call_requires_tool_name() -> None:
    with pytest.raises(ValidationError):
        ToolCall.model_validate({"span_id": "s"})


def test_tool_call_requires_span_id() -> None:
    with pytest.raises(ValidationError):
        ToolCall.model_validate({"tool_name": "lookup"})


def test_tool_call_rejects_empty_strings() -> None:
    # min_length=1 on tool_name and span_id is the contract: an
    # empty string cannot anchor a citation in the report.
    with pytest.raises(ValidationError):
        ToolCall.model_validate(
            {"tool_name": "", "span_id": "s"}
        )
    with pytest.raises(ValidationError):
        ToolCall.model_validate(
            {"tool_name": "lookup", "span_id": ""}
        )


def test_routing_decision_requires_target_agent_and_span_id() -> (
    None
):
    with pytest.raises(ValidationError):
        RoutingDecision.model_validate({"span_id": "s"})
    with pytest.raises(ValidationError):
        RoutingDecision.model_validate(
            {"target_agent": "billing"}
        )


def test_step_count_total_must_match_span_id_count() -> (
    None
):
    # The cross-field validator catches a frequent fetcher bug:
    # the writer recorded N step ids but stamped total_steps as
    # N-1 (off-by-one). Resolving silently with the wrong total
    # would let max_steps assertions silently pass or fail.
    with pytest.raises(ValidationError) as info:
        StepCount.model_validate(
            {
                "total_steps": 3,
                "step_span_ids": ["a", "b"],
            }
        )
    assert "does not match" in str(info.value)


def test_step_count_rejects_empty_span_id_string() -> None:
    with pytest.raises(ValidationError) as info:
        StepCount.model_validate(
            {
                "total_steps": 2,
                "step_span_ids": ["a", ""],
            }
        )
    assert "non-empty" in str(info.value)


def test_step_count_accepts_zero_steps_with_empty_list() -> (
    None
):
    record = StepCount.model_validate(
        {"total_steps": 0, "step_span_ids": []}
    )
    assert record.total_steps == 0
    assert record.step_span_ids == ()


def test_step_count_rejects_negative_total_steps() -> None:
    with pytest.raises(ValidationError):
        StepCount.model_validate(
            {"total_steps": -1, "step_span_ids": []}
        )


def test_generation_requires_span_id() -> None:
    with pytest.raises(ValidationError):
        Generation.model_validate({"model": "gpt-x"})


def test_generation_rejects_negative_token_counts() -> None:
    # NonNegativeInt on token fields prevents a fetcher bug
    # that emits a negative usage from being summed verbatim.
    with pytest.raises(ValidationError):
        Generation.model_validate(
            {
                "span_id": "g",
                "input_tokens": -1,
            }
        )


def test_generation_rejects_negative_cost() -> None:
    # ge=0 on cost fields. A negative cost in the trace would
    # otherwise allow max_total_cost_usd to silently pass.
    with pytest.raises(ValidationError):
        Generation.model_validate(
            {
                "span_id": "g",
                "total_cost_usd": -0.01,
            }
        )


def test_generation_accepts_minimal_well_formed_record() -> (
    None
):
    record = Generation.model_validate({"span_id": "g"})
    assert record.span_id == "g"
    assert record.total_tokens is None
    assert record.total_cost_usd is None
