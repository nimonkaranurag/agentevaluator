"""
Tests for the three observability log resolvers (path + parsed payload).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evaluate_agent.scoring import (
    ObservabilityLogMalformedError,
    ResolvedRoutingDecisionLog,
    ResolvedStepCount,
    ResolvedToolCallLog,
    resolve_routing_decision_log,
    resolve_step_count,
    resolve_tool_call_log,
    routing_decision_log_path,
    step_count_path,
    tool_call_log_path,
)


def _seed_jsonl(
    case_dir: Path, filename: str, lines: list[dict]
) -> Path:
    target = case_dir / "trace" / "observability" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(line) for line in lines),
        encoding="utf-8",
    )
    return target


def _seed_step_count(case_dir: Path, payload: dict) -> Path:
    target = (
        case_dir
        / "trace"
        / "observability"
        / "step_count.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class TestPathHelpers:
    def test_tool_call_log_path_shape(self, tmp_path):
        assert tool_call_log_path(tmp_path) == (
            tmp_path
            / "trace"
            / "observability"
            / "tool_calls.jsonl"
        )

    def test_routing_decision_log_path_shape(
        self, tmp_path
    ):
        assert routing_decision_log_path(tmp_path) == (
            tmp_path
            / "trace"
            / "observability"
            / "routing_decisions.jsonl"
        )

    def test_step_count_path_shape(self, tmp_path):
        assert step_count_path(tmp_path) == (
            tmp_path
            / "trace"
            / "observability"
            / "step_count.json"
        )

    def test_path_helpers_are_pure(self, tmp_path):
        tool_call_log_path(tmp_path)
        assert not (
            tmp_path / "trace" / "observability"
        ).exists()


class TestResolveToolCallLog:
    def test_returns_none_when_absent(self, tmp_path):
        assert resolve_tool_call_log(tmp_path) is None

    def test_returns_resolved_when_present(self, tmp_path):
        target = _seed_jsonl(
            tmp_path,
            "tool_calls.jsonl",
            [
                {"tool_name": "search", "span_id": "s1"},
                {
                    "tool_name": "transfer",
                    "span_id": "s2",
                },
            ],
        )
        result = resolve_tool_call_log(tmp_path)
        assert isinstance(result, ResolvedToolCallLog)
        assert result.path == target
        assert len(result.entries) == 2
        assert result.entries[0].tool_name == "search"

    def test_raises_on_malformed_json(self, tmp_path):
        target = (
            tmp_path
            / "trace"
            / "observability"
            / "tool_calls.jsonl"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("not-json\n", encoding="utf-8")
        with pytest.raises(
            ObservabilityLogMalformedError
        ) as info:
            resolve_tool_call_log(tmp_path)
        assert info.value.path == target

    def test_raises_on_schema_violation(self, tmp_path):
        _seed_jsonl(
            tmp_path,
            "tool_calls.jsonl",
            [{"tool_name": "search"}],
        )
        with pytest.raises(ObservabilityLogMalformedError):
            resolve_tool_call_log(tmp_path)


class TestResolveRoutingDecisionLog:
    def test_returns_none_when_absent(self, tmp_path):
        assert (
            resolve_routing_decision_log(tmp_path) is None
        )

    def test_returns_resolved_when_present(self, tmp_path):
        target = _seed_jsonl(
            tmp_path,
            "routing_decisions.jsonl",
            [
                {
                    "target_agent": "flight_specialist",
                    "span_id": "r1",
                },
            ],
        )
        result = resolve_routing_decision_log(tmp_path)
        assert isinstance(
            result, ResolvedRoutingDecisionLog
        )
        assert result.path == target
        assert len(result.entries) == 1
        assert (
            result.entries[0].target_agent
            == "flight_specialist"
        )

    def test_raises_on_malformed(self, tmp_path):
        target = (
            tmp_path
            / "trace"
            / "observability"
            / "routing_decisions.jsonl"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '{"target_agent": "ok"}\n',
            encoding="utf-8",
        )
        with pytest.raises(ObservabilityLogMalformedError):
            resolve_routing_decision_log(tmp_path)


class TestResolveStepCount:
    def test_returns_none_when_absent(self, tmp_path):
        assert resolve_step_count(tmp_path) is None

    def test_returns_resolved_when_present(self, tmp_path):
        target = _seed_step_count(
            tmp_path,
            {
                "total_steps": 3,
                "step_span_ids": ["a", "b", "c"],
            },
        )
        result = resolve_step_count(tmp_path)
        assert isinstance(result, ResolvedStepCount)
        assert result.path == target
        assert result.record.total_steps == 3
        assert result.record.step_span_ids == (
            "a",
            "b",
            "c",
        )

    def test_raises_on_malformed_json(self, tmp_path):
        target = (
            tmp_path
            / "trace"
            / "observability"
            / "step_count.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{nope", encoding="utf-8")
        with pytest.raises(ObservabilityLogMalformedError):
            resolve_step_count(tmp_path)

    def test_raises_on_length_mismatch(self, tmp_path):
        _seed_step_count(
            tmp_path,
            {
                "total_steps": 5,
                "step_span_ids": ["just_one"],
            },
        )
        with pytest.raises(
            ObservabilityLogMalformedError
        ) as info:
            resolve_step_count(tmp_path)
        assert info.value.line_number is None


class TestResolvedDataclassesFrozen:
    def test_tool_call_log_frozen(self, tmp_path):
        _seed_jsonl(
            tmp_path,
            "tool_calls.jsonl",
            [{"tool_name": "x", "span_id": "y"}],
        )
        result = resolve_tool_call_log(tmp_path)
        try:
            result.path = tmp_path  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError(
            "ResolvedToolCallLog is not frozen"
        )

    def test_routing_decision_log_frozen(self, tmp_path):
        _seed_jsonl(
            tmp_path,
            "routing_decisions.jsonl",
            [
                {
                    "target_agent": "a",
                    "span_id": "b",
                }
            ],
        )
        result = resolve_routing_decision_log(tmp_path)
        try:
            result.entries = ()  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError(
            "ResolvedRoutingDecisionLog is not frozen"
        )

    def test_step_count_frozen(self, tmp_path):
        _seed_step_count(
            tmp_path,
            {
                "total_steps": 1,
                "step_span_ids": ["a"],
            },
        )
        result = resolve_step_count(tmp_path)
        try:
            result.record = result.record  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError(
            "ResolvedStepCount is not frozen"
        )
