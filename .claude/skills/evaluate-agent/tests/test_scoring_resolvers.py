"""
Failure-mode tests for parse_jsonl_log, parse_single_json_log, and the four resolver wrappers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import (
    write_generations,
    write_routing_decisions,
    write_step_count,
    write_tool_calls,
)
from evaluate_agent.common.errors.scoring import (
    ObservabilityLogMalformedError,
)
from evaluate_agent.scoring.observability.schema import (
    Generation,
    StepCount,
    ToolCall,
)
from evaluate_agent.scoring.resolvers.log_resolvers.generation_log import (  # noqa: E501
    generation_log_path,
    resolve_generation_log,
)
from evaluate_agent.scoring.resolvers.log_resolvers.routing_decision_log import (  # noqa: E501
    resolve_routing_decision_log,
    routing_decision_log_path,
)
from evaluate_agent.scoring.resolvers.log_resolvers.tool_call_log import (  # noqa: E501
    resolve_tool_call_log,
    tool_call_log_path,
)
from evaluate_agent.scoring.resolvers.other_resolvers.dom_snapshot import (  # noqa: E501
    OversizedDOMSnapshot,
    extract_visible_text,
    resolve_post_submit_dom_snapshot,
)
from evaluate_agent.scoring.resolvers.other_resolvers.step_count import (  # noqa: E501
    resolve_step_count,
    step_count_path,
)
from evaluate_agent.scoring.resolvers.utils.parsing import (
    parse_jsonl_log,
    parse_single_json_log,
)


def test_parse_jsonl_log_skips_blank_lines(
    tmp_path: Path,
) -> None:
    # Trailing newlines + blank separators are routine in
    # JSONL files. The parser should treat them as no-ops
    # rather than fail with a parse error.
    path = tmp_path / "log.jsonl"
    path.write_text(
        '{"tool_name":"a","span_id":"s1"}\n'
        "\n"
        '{"tool_name":"b","span_id":"s2"}\n',
        encoding="utf-8",
    )
    entries = parse_jsonl_log(path, ToolCall)
    assert len(entries) == 2


def test_parse_jsonl_log_raises_with_line_number(
    tmp_path: Path,
) -> None:
    path = tmp_path / "log.jsonl"
    path.write_text(
        '{"tool_name":"a","span_id":"s1"}\n' "{NOT JSON}\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ObservabilityLogMalformedError
    ) as info:
        parse_jsonl_log(path, ToolCall)
    assert info.value.line_number == 2
    assert "invalid JSON" in info.value.parse_error


def test_parse_jsonl_log_raises_with_schema_violation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "log.jsonl"
    path.write_text(
        '{"tool_name":"a","span_id":"s1"}\n'
        '{"span_id":"s2"}\n',  # missing tool_name
        encoding="utf-8",
    )
    with pytest.raises(
        ObservabilityLogMalformedError
    ) as info:
        parse_jsonl_log(path, ToolCall)
    assert info.value.line_number == 2
    assert "schema violation" in info.value.parse_error


def test_parse_single_json_log_raises_without_line_number(
    tmp_path: Path,
) -> None:
    # step_count.json is a single document; the parser must
    # signal "whole document" by leaving line_number=None so
    # the recovery hint reads "the file body" not "line N".
    path = tmp_path / "step_count.json"
    path.write_text("{not: valid", encoding="utf-8")
    with pytest.raises(
        ObservabilityLogMalformedError
    ) as info:
        parse_single_json_log(path, StepCount)
    assert info.value.line_number is None


def test_resolve_tool_call_log_returns_none_for_missing_file(
    case_dir: Path,
) -> None:
    assert resolve_tool_call_log(case_dir) is None
    # The path helper still resolves to the conventional location
    # so the inconclusive recovery message can name it.
    assert (
        tool_call_log_path(case_dir).name
        == "tool_calls.jsonl"
    )


def test_resolve_tool_call_log_returns_entries_in_order(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "a", "span_id": "s1"},
            {"tool_name": "b", "span_id": "s2"},
            {"tool_name": "a", "span_id": "s3"},
        ],
    )
    log = resolve_tool_call_log(case_dir)
    assert log is not None
    assert [e.tool_name for e in log.entries] == [
        "a",
        "b",
        "a",
    ]


def test_resolve_routing_decision_log_returns_none_when_absent(
    case_dir: Path,
) -> None:
    assert resolve_routing_decision_log(case_dir) is None
    assert (
        routing_decision_log_path(case_dir).name
        == "routing_decisions.jsonl"
    )


def test_resolve_routing_decision_log_parses_well_formed_entries(
    case_dir: Path,
) -> None:
    write_routing_decisions(
        case_dir,
        [
            {"target_agent": "billing", "span_id": "r1"},
            {"target_agent": "support", "span_id": "r2"},
        ],
    )
    log = resolve_routing_decision_log(case_dir)
    assert log is not None
    assert {e.target_agent for e in log.entries} == {
        "billing",
        "support",
    }


def test_resolve_generation_log_returns_none_when_absent(
    case_dir: Path,
) -> None:
    assert resolve_generation_log(case_dir) is None
    assert (
        generation_log_path(case_dir).name
        == "generations.jsonl"
    )


def test_resolve_generation_log_parses_entries(
    case_dir: Path,
) -> None:
    write_generations(
        case_dir,
        [
            {
                "span_id": "g1",
                "total_tokens": 100,
                "total_cost_usd": 0.01,
            },
            {
                "span_id": "g2",
                "total_tokens": 200,
            },
        ],
    )
    log = resolve_generation_log(case_dir)
    assert log is not None
    assert len(log.entries) == 2
    assert log.entries[1].total_cost_usd is None


def test_resolve_step_count_returns_none_when_absent(
    case_dir: Path,
) -> None:
    assert resolve_step_count(case_dir) is None
    assert (
        step_count_path(case_dir).name == "step_count.json"
    )


def test_resolve_step_count_parses_well_formed_record(
    case_dir: Path,
) -> None:
    write_step_count(
        case_dir,
        {
            "total_steps": 2,
            "step_span_ids": ["a", "b"],
        },
    )
    record = resolve_step_count(case_dir)
    assert record is not None
    assert record.record.total_steps == 2


def test_resolve_step_count_propagates_schema_violation(
    case_dir: Path,
) -> None:
    write_step_count(
        case_dir,
        {
            "total_steps": 5,
            "step_span_ids": ["a"],
        },
    )
    with pytest.raises(ObservabilityLogMalformedError):
        resolve_step_count(case_dir)


def test_dom_snapshot_returns_none_when_directory_missing(
    case_dir: Path,
) -> None:
    assert (
        resolve_post_submit_dom_snapshot(
            case_dir, max_dom_bytes=1024 * 1024
        )
        is None
    )


def test_dom_snapshot_returns_none_when_no_post_submit_files(
    case_dir: Path,
) -> None:
    # Landing-only captures must NOT be picked up — the resolver
    # is post_submit-specific. A regression that loosened the
    # filename pattern would silently score against the wrong
    # snapshot.
    dom_dir = case_dir / "trace" / "dom"
    dom_dir.mkdir(parents=True)
    (dom_dir / "step-001-landing.html").write_text(
        "<html></html>", encoding="utf-8"
    )
    assert (
        resolve_post_submit_dom_snapshot(
            case_dir, max_dom_bytes=1024 * 1024
        )
        is None
    )


def test_dom_snapshot_picks_highest_step_number(
    case_dir: Path,
) -> None:
    dom_dir = case_dir / "trace" / "dom"
    dom_dir.mkdir(parents=True)
    (dom_dir / "step-001-after_submit.html").write_text(
        "<html><body>old</body></html>", encoding="utf-8"
    )
    (dom_dir / "step-009-after_submit.html").write_text(
        "<html><body>latest</body></html>",
        encoding="utf-8",
    )
    snapshot = resolve_post_submit_dom_snapshot(
        case_dir, max_dom_bytes=1024 * 1024
    )
    assert snapshot is not None
    assert snapshot.path.name == (
        "step-009-after_submit.html"
    )
    assert "latest" in snapshot.visible_text


def test_dom_snapshot_oversized_returns_metadata_only(
    case_dir: Path,
) -> None:
    # The oversized branch must NOT load the file into memory:
    # the test sets max_dom_bytes below the file size and asserts
    # the resolver returns the metadata-only sentinel rather than
    # an OOM-prone ResolvedDOMSnapshot.
    dom_dir = case_dir / "trace" / "dom"
    dom_dir.mkdir(parents=True)
    payload = "x" * 2048
    file = dom_dir / "step-001-after_submit.html"
    file.write_text(
        f"<html><body>{payload}</body></html>",
        encoding="utf-8",
    )
    out = resolve_post_submit_dom_snapshot(
        case_dir, max_dom_bytes=512
    )
    assert isinstance(out, OversizedDOMSnapshot)
    assert out.size_bytes > 512
    assert out.cap_bytes == 512


def test_extract_visible_text_strips_scripts_and_styles() -> (
    None
):
    html = (
        "<html><head>"
        "<style>.a{color:red}</style>"
        "<script>alert(1)</script>"
        "</head><body>"
        "<noscript>noscript-text</noscript>"
        "<p>visible <strong>text</strong></p>"
        "<!-- a comment -->"
        "</body></html>"
    )
    text = extract_visible_text(html)
    assert "alert" not in text
    assert "color" not in text
    assert "noscript-text" not in text
    assert "comment" not in text
    assert "visible text" in text


def test_extract_visible_text_collapses_whitespace_runs() -> (
    None
):
    text = extract_visible_text(
        "<p>spaced     out</p>\n\n<p>second\tline</p>"
    )
    assert text == "spaced out second line"
