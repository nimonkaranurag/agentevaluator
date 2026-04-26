"""
Tests for resolve_page_errors_log (path + parsed payload).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evaluate_agent.scoring import (
    PageErrorEntry,
    ResolvedPageErrorsLog,
    StructuredLogParseError,
    page_errors_log_path,
    resolve_page_errors_log,
)


def _seed_jsonl(case_dir: Path, lines: list[dict]) -> Path:
    target = case_dir / "trace" / "page_errors.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(line) for line in lines),
        encoding="utf-8",
    )
    return target


class TestPathConstruction:
    def test_path_under_trace_subdir(self, tmp_path):
        assert page_errors_log_path(tmp_path) == (
            tmp_path / "trace" / "page_errors.jsonl"
        )

    def test_path_pure_computation(self, tmp_path):
        page_errors_log_path(tmp_path)
        assert not (
            tmp_path / "trace" / "page_errors.jsonl"
        ).exists()


class TestResolvedShape:
    def test_returns_none_when_log_absent(self, tmp_path):
        assert resolve_page_errors_log(tmp_path) is None

    def test_returns_none_when_path_is_directory(
        self, tmp_path
    ):
        target = tmp_path / "trace" / "page_errors.jsonl"
        target.mkdir(parents=True, exist_ok=True)
        assert resolve_page_errors_log(tmp_path) is None

    def test_resolved_dataclass_carries_path_and_entries(
        self, tmp_path
    ):
        target = _seed_jsonl(
            tmp_path,
            [
                {
                    "ts": "2026-04-26T12:00:00.000+00:00",
                    "message": "X happened",
                }
            ],
        )
        result = resolve_page_errors_log(tmp_path)
        assert isinstance(result, ResolvedPageErrorsLog)
        assert result.path == target
        assert len(result.entries) == 1
        assert isinstance(result.entries[0], PageErrorEntry)
        assert result.entries[0].message == "X happened"

    def test_empty_log_returns_zero_entries(self, tmp_path):
        target = tmp_path / "trace" / "page_errors.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        result = resolve_page_errors_log(tmp_path)
        assert isinstance(result, ResolvedPageErrorsLog)
        assert result.path == target
        assert result.entries == ()

    def test_multiple_entries_preserved_in_order(
        self, tmp_path
    ):
        _seed_jsonl(
            tmp_path,
            [
                {
                    "ts": "2026-04-26T12:00:00.000+00:00",
                    "message": "first",
                },
                {
                    "ts": "2026-04-26T12:00:01.000+00:00",
                    "message": "second",
                },
                {
                    "ts": "2026-04-26T12:00:02.000+00:00",
                    "message": "third",
                },
            ],
        )
        result = resolve_page_errors_log(tmp_path)
        assert tuple(
            entry.message for entry in result.entries
        ) == ("first", "second", "third")


class TestMalformedLog:
    def test_invalid_json_raises_with_line_number(
        self, tmp_path
    ):
        target = tmp_path / "trace" / "page_errors.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '{"ts": "2026-04-26T12:00:00.000+00:00", '
            '"message": "ok"}\n'
            "completely-broken\n",
            encoding="utf-8",
        )
        with pytest.raises(StructuredLogParseError) as info:
            resolve_page_errors_log(tmp_path)
        assert info.value.line_number == 2
        assert info.value.path == target
        assert "invalid JSON" in info.value.parse_error

    def test_schema_violation_raises_with_line_number(
        self, tmp_path
    ):
        target = tmp_path / "trace" / "page_errors.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '{"ts": "2026-04-26T12:00:00.000+00:00", '
            '"message": "ok"}\n'
            '{"ts": "2026-04-26T12:00:01.000+00:00"}\n',
            encoding="utf-8",
        )
        with pytest.raises(StructuredLogParseError) as info:
            resolve_page_errors_log(tmp_path)
        assert info.value.line_number == 2
        assert "schema violation" in info.value.parse_error
        assert "PageErrorEntry" in info.value.parse_error
