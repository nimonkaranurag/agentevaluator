"""Shared fixtures and on-disk writers for the evaluate-agent test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pytest
from evaluate_agent.artifact_layout import (
    GENERATION_LOG_FILENAME,
    OBSERVABILITY_SUBDIR,
    ROUTING_DECISION_LOG_FILENAME,
    STEP_COUNT_FILENAME,
    TOOL_CALL_LOG_FILENAME,
    TRACE_SUBDIR,
)


@pytest.fixture
def case_dir(tmp_path: Path) -> Path:
    path = tmp_path / "case"
    path.mkdir()
    return path


@pytest.fixture
def observability_dir(case_dir: Path) -> Path:
    path = case_dir / TRACE_SUBDIR / OBSERVABILITY_SUBDIR
    path.mkdir(parents=True)
    return path


def write_jsonl(
    path: Path, entries: Iterable[dict[str, Any]]
) -> Path:
    body = "\n".join(json.dumps(e) for e in entries) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def write_tool_calls(
    case_dir: Path, entries: Iterable[dict[str, Any]]
) -> Path:
    return write_jsonl(
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / TOOL_CALL_LOG_FILENAME,
        entries,
    )


def write_routing_decisions(
    case_dir: Path, entries: Iterable[dict[str, Any]]
) -> Path:
    return write_jsonl(
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / ROUTING_DECISION_LOG_FILENAME,
        entries,
    )


def write_generations(
    case_dir: Path, entries: Iterable[dict[str, Any]]
) -> Path:
    return write_jsonl(
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / GENERATION_LOG_FILENAME,
        entries,
    )


def write_step_count(
    case_dir: Path, document: dict[str, Any]
) -> Path:
    path = (
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / STEP_COUNT_FILENAME
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document) + "\n", encoding="utf-8"
    )
    return path
