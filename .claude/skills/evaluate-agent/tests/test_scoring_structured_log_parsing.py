"""
Tests for parse_jsonl_log and parse_single_json_log helpers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evaluate_agent.scoring import (
    StepCount,
    StructuredLogParseError,
    ToolCall,
    parse_jsonl_log,
    parse_single_json_log,
)


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(line) for line in lines)
    path.write_text(payload, encoding="utf-8")


class TestParseJsonlLog:
    def test_empty_file_returns_empty_tuple(self, tmp_path):
        target = tmp_path / "empty.jsonl"
        target.write_text("", encoding="utf-8")
        result = parse_jsonl_log(target, ToolCall)
        assert result == ()

    def test_blank_lines_skipped(self, tmp_path):
        target = tmp_path / "blanks.jsonl"
        target.write_text(
            '\n{"tool_name": "a", "span_id": "1"}\n\n'
            '{"tool_name": "b", "span_id": "2"}\n\n',
            encoding="utf-8",
        )
        result = parse_jsonl_log(target, ToolCall)
        assert len(result) == 2
        assert result[0].tool_name == "a"
        assert result[1].tool_name == "b"

    def test_each_line_parsed_into_model(self, tmp_path):
        target = tmp_path / "good.jsonl"
        _write_jsonl(
            target,
            [
                {
                    "tool_name": "search",
                    "span_id": "span-1",
                },
                {
                    "tool_name": "transfer",
                    "span_id": "span-2",
                    "arguments": {"amount": 100},
                },
            ],
        )
        result = parse_jsonl_log(target, ToolCall)
        assert isinstance(result, tuple)
        assert all(
            isinstance(item, ToolCall) for item in result
        )

    def test_invalid_json_raises_with_line_number(
        self, tmp_path
    ):
        target = tmp_path / "bad.jsonl"
        target.write_text(
            '{"tool_name": "ok", "span_id": "1"}\n'
            "not-json-at-all\n",
            encoding="utf-8",
        )
        with pytest.raises(StructuredLogParseError) as info:
            parse_jsonl_log(target, ToolCall)
        assert info.value.line_number == 2
        assert info.value.path == target
        assert "invalid JSON" in info.value.parse_error

    def test_schema_violation_raises_with_line_number(
        self, tmp_path
    ):
        target = tmp_path / "bad.jsonl"
        target.write_text(
            '{"tool_name": "ok", "span_id": "1"}\n'
            '{"tool_name": "missing_span"}\n',
            encoding="utf-8",
        )
        with pytest.raises(StructuredLogParseError) as info:
            parse_jsonl_log(target, ToolCall)
        assert info.value.line_number == 2
        assert "schema violation" in info.value.parse_error
        assert "ToolCall" in info.value.parse_error

    def test_first_line_failure_reports_line_one(
        self, tmp_path
    ):
        target = tmp_path / "bad.jsonl"
        target.write_text(
            "broken-first-line\n", encoding="utf-8"
        )
        with pytest.raises(StructuredLogParseError) as info:
            parse_jsonl_log(target, ToolCall)
        assert info.value.line_number == 1


class TestParseSingleJsonLog:
    def test_valid_object(self, tmp_path):
        target = tmp_path / "ok.json"
        target.write_text(
            json.dumps(
                {
                    "total_steps": 2,
                    "step_span_ids": ["a", "b"],
                }
            ),
            encoding="utf-8",
        )
        result = parse_single_json_log(target, StepCount)
        assert isinstance(result, StepCount)
        assert result.total_steps == 2

    def test_invalid_json_raises_without_line(
        self, tmp_path
    ):
        target = tmp_path / "bad.json"
        target.write_text("{nope", encoding="utf-8")
        with pytest.raises(StructuredLogParseError) as info:
            parse_single_json_log(target, StepCount)
        assert info.value.line_number is None
        assert info.value.path == target
        assert "invalid JSON" in info.value.parse_error

    def test_schema_violation_raises_without_line(
        self, tmp_path
    ):
        target = tmp_path / "bad.json"
        target.write_text(
            json.dumps(
                {
                    "total_steps": 5,
                    "step_span_ids": ["only_one"],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(StructuredLogParseError) as info:
            parse_single_json_log(target, StepCount)
        assert info.value.line_number is None
        assert "schema violation" in info.value.parse_error
        assert "StepCount" in info.value.parse_error
