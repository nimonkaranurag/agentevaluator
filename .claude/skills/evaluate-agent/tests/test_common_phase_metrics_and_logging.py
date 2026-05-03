"""
Failure-mode tests for the MetricsCollector phase recorder, the JSON/text log formatters, and configure_script_logging.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pytest
from evaluate_agent.common.phase_metrics import (
    MetricsCollector,
    PhaseMetric,
    ScriptMetrics,
)
from evaluate_agent.common.script_logging import (
    JsonLogFormatter,
    TextLogFormatter,
    configure_script_logging,
)


def test_phase_records_capture_in_completion_order() -> (
    None
):
    # Phase order matters: the renderer reads it back as the
    # narrative shape of the script's run. A regression that
    # records phases in entry order would scramble the
    # timeline.
    collector = MetricsCollector(script_name="demo")
    with collector.phase("first"):
        pass
    with collector.phase("second"):
        pass
    document = collector.build(exit_status="success")
    assert [p.name for p in document.phases] == [
        "first",
        "second",
    ]


def test_phase_records_non_negative_duration() -> None:
    collector = MetricsCollector(script_name="demo")
    with collector.phase("p"):
        pass
    document = collector.build(exit_status="success")
    assert document.phases[0].duration_ms >= 0


def test_phase_record_runs_finally_on_exception() -> None:
    # The phase context manager must record the duration even
    # when the body raises — otherwise a script that fails
    # mid-phase produces a metrics document missing the
    # phase that actually crashed, hiding the relevant signal.
    collector = MetricsCollector(script_name="demo")
    with pytest.raises(RuntimeError):
        with collector.phase("crashes"):
            raise RuntimeError("boom")
    document = collector.build(exit_status="error")
    assert [p.name for p in document.phases] == ["crashes"]


def test_set_context_round_trips_to_document() -> None:
    collector = MetricsCollector(script_name="demo")
    collector.set_context(
        run_id="20260425T173000Z", case_id="c"
    )
    document = collector.build(exit_status="success")
    assert document.context.run_id == ("20260425T173000Z")
    assert document.context.case_id == "c"


def test_set_context_with_none_clears_field() -> None:
    # Passing None clears the field — useful when a script
    # binds a context value tentatively then learns it was
    # the wrong key.
    collector = MetricsCollector(script_name="demo")
    collector.set_context(case_id="c")
    collector.set_context(case_id=None)
    document = collector.build(exit_status="success")
    assert document.context.case_id is None


def test_emit_if_configured_no_op_when_path_none(
    tmp_path: Path,
) -> None:
    collector = MetricsCollector(script_name="demo")
    collector.emit_if_configured(
        None, exit_status="success"
    )
    # No file should be written, no exception raised.


def test_emit_if_configured_writes_valid_json(
    tmp_path: Path,
) -> None:
    collector = MetricsCollector(script_name="demo")
    with collector.phase("p"):
        pass
    target = tmp_path / "metrics.json"
    collector.emit_if_configured(
        target, exit_status="success"
    )
    payload = json.loads(target.read_text())
    assert payload["script"] == "demo"
    assert payload["exit_status"] == "success"
    assert len(payload["phases"]) == 1


def test_emit_if_configured_creates_parent_dirs(
    tmp_path: Path,
) -> None:
    # CI invocations land the metrics file in a per-run
    # directory that may not exist yet; the emitter must
    # create the path rather than fail with FileNotFoundError.
    collector = MetricsCollector(script_name="demo")
    target = tmp_path / "deep" / "nested" / "metrics.json"
    collector.emit_if_configured(
        target, exit_status="success"
    )
    assert target.is_file()


def test_text_formatter_renders_level_and_context() -> None:
    record = logging.LogRecord(
        name="demo",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="something happened",
        args=(),
        exc_info=None,
    )
    record.run_id = "20260425T173000Z"
    out = TextLogFormatter().format(record)
    assert "[INFO]" in out
    assert "demo:" in out
    assert "run_id=20260425T173000Z" in out


def test_json_formatter_serializes_context_fields() -> None:
    # Structured logs are the CI consumer's contract — every
    # context field declared in CONTEXT_FIELD_NAMES must round
    # trip into the JSON payload.
    record = logging.LogRecord(
        name="demo",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event",
        args=(),
        exc_info=None,
    )
    record.case_id = "c"
    record.assertion_kind = "must_call"
    out = JsonLogFormatter().format(record)
    payload = json.loads(out)
    assert payload["level"] == "INFO"
    assert payload["case_id"] == "c"
    assert payload["assertion_kind"] == "must_call"


def test_configure_script_logging_rejects_invalid_format() -> (
    None
):
    with pytest.raises(ValueError):
        configure_script_logging(
            script_name="demo", log_format="xml"
        )


def test_configure_script_logging_replaces_handlers() -> (
    None
):
    # The harness may install handlers at startup; the script
    # configurer must remove them so log records aren't
    # double-written. A regression here would emit each line
    # to stderr twice in CI.
    root = logging.getLogger()
    root.addHandler(logging.NullHandler())
    starting = len(root.handlers)
    configure_script_logging(
        script_name="demo", log_format="text"
    )
    assert len(root.handlers) == 1
    assert starting >= 1
