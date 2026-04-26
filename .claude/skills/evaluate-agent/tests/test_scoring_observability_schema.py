"""
Tests for the on-disk observability log schemas.
"""

from __future__ import annotations

import pytest
from evaluate_agent.scoring import (
    RoutingDecision,
    StepCount,
    ToolCall,
)
from pydantic import ValidationError


class TestToolCall:
    def test_minimal_construction(self):
        entry = ToolCall(
            tool_name="search",
            span_id="span-001",
        )
        assert entry.tool_name == "search"
        assert entry.span_id == "span-001"
        assert entry.arguments is None
        assert entry.result is None
        assert entry.timestamp is None

    def test_full_construction(self):
        entry = ToolCall(
            tool_name="search",
            span_id="span-001",
            arguments={"query": "JFK"},
            result="2 flights found",
            timestamp="2026-04-26T10:00:00Z",
        )
        assert entry.arguments == {"query": "JFK"}
        assert entry.result == "2 flights found"
        assert entry.timestamp == "2026-04-26T10:00:00Z"

    def test_tool_name_required(self):
        with pytest.raises(ValidationError):
            ToolCall(span_id="span-001")  # type: ignore[call-arg]

    def test_tool_name_min_length(self):
        with pytest.raises(ValidationError):
            ToolCall(tool_name="", span_id="span-001")

    def test_span_id_required(self):
        with pytest.raises(ValidationError):
            ToolCall(tool_name="search")  # type: ignore[call-arg]

    def test_span_id_min_length(self):
        with pytest.raises(ValidationError):
            ToolCall(tool_name="search", span_id="")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            ToolCall(
                tool_name="search",
                span_id="span-001",
                surprise="nope",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        entry = ToolCall(
            tool_name="search", span_id="span-001"
        )
        with pytest.raises(ValidationError):
            entry.tool_name = "transfer"  # type: ignore[misc]


class TestRoutingDecision:
    def test_minimal_construction(self):
        entry = RoutingDecision(
            target_agent="flight_specialist",
            span_id="span-002",
        )
        assert entry.target_agent == "flight_specialist"
        assert entry.span_id == "span-002"
        assert entry.from_agent is None
        assert entry.reason is None
        assert entry.timestamp is None

    def test_full_construction(self):
        entry = RoutingDecision(
            target_agent="flight_specialist",
            span_id="span-002",
            from_agent="orchestrator",
            reason="user asked about flights",
            timestamp="2026-04-26T10:00:01Z",
        )
        assert entry.from_agent == "orchestrator"
        assert entry.reason == "user asked about flights"

    def test_target_agent_required(self):
        with pytest.raises(ValidationError):
            RoutingDecision(span_id="span-002")  # type: ignore[call-arg]

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            RoutingDecision(
                target_agent="flight_specialist",
                span_id="span-002",
                surprise="nope",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        entry = RoutingDecision(
            target_agent="x", span_id="y"
        )
        with pytest.raises(ValidationError):
            entry.target_agent = "z"  # type: ignore[misc]


class TestStepCount:
    def test_zero_steps(self):
        record = StepCount(
            total_steps=0,
            step_span_ids=(),
        )
        assert record.total_steps == 0
        assert record.step_span_ids == ()

    def test_matching_lengths(self):
        record = StepCount(
            total_steps=3,
            step_span_ids=("a", "b", "c"),
        )
        assert record.total_steps == 3
        assert record.step_span_ids == ("a", "b", "c")

    def test_total_steps_negative_rejected(self):
        with pytest.raises(ValidationError):
            StepCount(total_steps=-1, step_span_ids=())

    def test_length_mismatch_rejected(self):
        with pytest.raises(ValidationError) as info:
            StepCount(
                total_steps=2,
                step_span_ids=("only_one",),
            )
        message = str(info.value)
        assert "step_span_ids" in message
        assert "total_steps" in message

    def test_empty_span_id_rejected(self):
        with pytest.raises(ValidationError):
            StepCount(
                total_steps=2,
                step_span_ids=("a", ""),
            )

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            StepCount(
                total_steps=0,
                step_span_ids=(),
                surprise="nope",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        record = StepCount(
            total_steps=1, step_span_ids=("a",)
        )
        with pytest.raises(ValidationError):
            record.total_steps = 2  # type: ignore[misc]
