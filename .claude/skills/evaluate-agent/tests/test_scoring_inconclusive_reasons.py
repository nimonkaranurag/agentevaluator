"""
Tests for the discriminated InconclusiveReason union.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.scoring import (
    BaselineTraceArtifactMissing,
    BaselineTraceLogMalformed,
    DOMSnapshotUnavailable,
    InconclusiveReason,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
    StructuredLogParseError,
)
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
)

_REASON_ADAPTER = TypeAdapter(InconclusiveReason)


class _ReasonContainer(BaseModel):
    item: InconclusiveReason = Field(...)


class TestDOMSnapshotUnavailable:
    def test_kind_literal(self):
        reason = DOMSnapshotUnavailable(
            expected_artifact_dir=Path(
                "/tmp/case/trace/dom"
            ),
        )
        assert reason.kind == "dom_snapshot_unavailable"

    def test_expected_artifact_dir_required(self):
        with pytest.raises(ValidationError):
            DOMSnapshotUnavailable()  # type: ignore[call-arg]

    def test_default_recovery_present(self):
        reason = DOMSnapshotUnavailable(
            expected_artifact_dir=Path(
                "/tmp/case/trace/dom"
            ),
        )
        assert "--submit" in reason.recovery
        assert "To proceed:" in reason.recovery

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            DOMSnapshotUnavailable(
                expected_artifact_dir=Path("/tmp/x"),
                extra="nope",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        reason = DOMSnapshotUnavailable(
            expected_artifact_dir=Path("/tmp/x")
        )
        with pytest.raises(ValidationError):
            reason.expected_artifact_dir = Path(  # type: ignore[misc]
                "/elsewhere"
            )


class TestObservabilitySourceMissing:
    def _build(self, **overrides):
        defaults = dict(
            needed_evidence="tool_call_log",
            expected_artifact_path=Path(
                "/tmp/case/trace/observability/"
                "tool_calls.jsonl"
            ),
        )
        defaults.update(overrides)
        return ObservabilitySourceMissing(**defaults)

    def test_kind_literal(self):
        reason = self._build()
        assert reason.kind == "observability_source_missing"

    @pytest.mark.parametrize(
        "evidence",
        [
            "tool_call_log",
            "routing_decision_log",
            "step_count",
        ],
    )
    def test_needed_evidence_accepted(self, evidence):
        reason = self._build(needed_evidence=evidence)
        assert reason.needed_evidence == evidence

    def test_unknown_evidence_rejected(self):
        with pytest.raises(ValidationError):
            self._build(needed_evidence="vibes")

    def test_expected_artifact_path_required(self):
        with pytest.raises(ValidationError):
            ObservabilitySourceMissing(
                needed_evidence="tool_call_log",
            )  # type: ignore[call-arg]

    def test_expected_artifact_path_preserved(self):
        target = Path("/tmp/elsewhere/log.jsonl")
        reason = self._build(expected_artifact_path=target)
        assert reason.expected_artifact_path == target

    def test_default_recovery_present(self):
        reason = self._build()
        assert "manifest.observability" in reason.recovery
        assert "expected_artifact_path" in reason.recovery
        assert "To proceed:" in reason.recovery

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            self._build(extra="nope")

    def test_frozen(self):
        reason = self._build()
        with pytest.raises(ValidationError):
            reason.needed_evidence = "step_count"  # type: ignore[misc]


class TestObservabilityLogMalformed:
    def _build(self, **overrides):
        defaults = dict(
            log_path=Path(
                "/tmp/case/trace/observability/"
                "tool_calls.jsonl"
            ),
            line_number=3,
            parse_error=("invalid JSON (Expecting value)"),
        )
        defaults.update(overrides)
        return ObservabilityLogMalformed(**defaults)

    def test_kind_literal(self):
        reason = self._build()
        assert reason.kind == "observability_log_malformed"

    def test_log_path_required(self):
        with pytest.raises(ValidationError):
            ObservabilityLogMalformed(
                line_number=1,
                parse_error="x",
            )  # type: ignore[call-arg]

    def test_parse_error_required(self):
        with pytest.raises(ValidationError):
            ObservabilityLogMalformed(
                log_path=Path("/tmp/x"),
                line_number=1,
            )  # type: ignore[call-arg]

    def test_parse_error_min_length(self):
        with pytest.raises(ValidationError):
            self._build(parse_error="")

    def test_line_number_optional(self):
        reason = self._build(line_number=None)
        assert reason.line_number is None

    def test_line_number_minimum(self):
        with pytest.raises(ValidationError):
            self._build(line_number=0)

    def test_default_recovery_present(self):
        reason = self._build()
        assert "log_path" in reason.recovery
        assert "schema" in reason.recovery
        assert "To proceed:" in reason.recovery

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            self._build(extra="nope")

    def test_frozen(self):
        reason = self._build()
        with pytest.raises(ValidationError):
            reason.parse_error = "different"  # type: ignore[misc]

    def test_from_error_classmethod_jsonl(self):
        error = StructuredLogParseError(
            path=Path(
                "/tmp/case/trace/observability/"
                "tool_calls.jsonl"
            ),
            line_number=4,
            parse_error="schema violation",
        )
        reason = ObservabilityLogMalformed.from_error(error)
        assert reason.log_path == error.path
        assert reason.line_number == 4
        assert reason.parse_error == "schema violation"

    def test_from_error_classmethod_single_json(self):
        error = StructuredLogParseError(
            path=Path(
                "/tmp/case/trace/observability/"
                "step_count.json"
            ),
            line_number=None,
            parse_error="invalid JSON",
        )
        reason = ObservabilityLogMalformed.from_error(error)
        assert reason.line_number is None


class TestDiscriminatedUnion:
    def test_validate_dom_branch(self):
        reason = _REASON_ADAPTER.validate_python(
            {
                "kind": "dom_snapshot_unavailable",
                "expected_artifact_dir": (
                    "/tmp/case/trace/dom"
                ),
            }
        )
        assert isinstance(reason, DOMSnapshotUnavailable)

    def test_validate_observability_branch(self):
        reason = _REASON_ADAPTER.validate_python(
            {
                "kind": "observability_source_missing",
                "needed_evidence": "tool_call_log",
                "expected_artifact_path": (
                    "/tmp/case/trace/observability/"
                    "tool_calls.jsonl"
                ),
            }
        )
        assert isinstance(
            reason, ObservabilitySourceMissing
        )

    def test_validate_malformed_branch(self):
        reason = _REASON_ADAPTER.validate_python(
            {
                "kind": "observability_log_malformed",
                "log_path": (
                    "/tmp/case/trace/observability/"
                    "tool_calls.jsonl"
                ),
                "line_number": 3,
                "parse_error": "invalid JSON",
            }
        )
        assert isinstance(reason, ObservabilityLogMalformed)

    def test_unknown_kind_rejected(self):
        with pytest.raises(ValidationError):
            _REASON_ADAPTER.validate_python(
                {
                    "kind": "unknown_reason",
                    "needed_evidence": "tool_call_log",
                }
            )

    def test_round_trip_dom_branch(self):
        wrapper = _ReasonContainer(
            item=DOMSnapshotUnavailable(
                expected_artifact_dir=Path("/tmp/x"),
            ),
        )
        text = wrapper.model_dump_json()
        reconstituted = (
            _ReasonContainer.model_validate_json(text)
        )
        assert reconstituted == wrapper

    def test_round_trip_observability_branch(self):
        wrapper = _ReasonContainer(
            item=ObservabilitySourceMissing(
                needed_evidence="routing_decision_log",
                expected_artifact_path=Path(
                    "/tmp/case/trace/observability/"
                    "routing_decisions.jsonl"
                ),
            ),
        )
        text = wrapper.model_dump_json()
        reconstituted = (
            _ReasonContainer.model_validate_json(text)
        )
        assert reconstituted == wrapper

    def test_round_trip_malformed_branch(self):
        wrapper = _ReasonContainer(
            item=ObservabilityLogMalformed(
                log_path=Path(
                    "/tmp/case/trace/observability/"
                    "tool_calls.jsonl"
                ),
                line_number=2,
                parse_error="invalid JSON",
            ),
        )
        text = wrapper.model_dump_json()
        reconstituted = (
            _ReasonContainer.model_validate_json(text)
        )
        assert reconstituted == wrapper

    def test_validate_baseline_artifact_missing_branch(
        self,
    ):
        reason = _REASON_ADAPTER.validate_python(
            {
                "kind": "baseline_trace_artifact_missing",
                "needed_artifact": "page_errors_log",
                "expected_artifact_path": (
                    "/tmp/case/trace/page_errors.jsonl"
                ),
            }
        )
        assert isinstance(
            reason, BaselineTraceArtifactMissing
        )

    def test_validate_baseline_log_malformed_branch(self):
        reason = _REASON_ADAPTER.validate_python(
            {
                "kind": "baseline_trace_log_malformed",
                "log_path": (
                    "/tmp/case/trace/page_errors.jsonl"
                ),
                "line_number": 2,
                "parse_error": "invalid JSON",
            }
        )
        assert isinstance(reason, BaselineTraceLogMalformed)

    def test_round_trip_baseline_artifact_missing(self):
        wrapper = _ReasonContainer(
            item=BaselineTraceArtifactMissing(
                needed_artifact="page_errors_log",
                expected_artifact_path=Path(
                    "/tmp/case/trace/page_errors.jsonl"
                ),
            ),
        )
        text = wrapper.model_dump_json()
        reconstituted = (
            _ReasonContainer.model_validate_json(text)
        )
        assert reconstituted == wrapper

    def test_round_trip_baseline_log_malformed(self):
        wrapper = _ReasonContainer(
            item=BaselineTraceLogMalformed(
                log_path=Path(
                    "/tmp/case/trace/page_errors.jsonl"
                ),
                line_number=4,
                parse_error="invalid JSON",
            ),
        )
        text = wrapper.model_dump_json()
        reconstituted = (
            _ReasonContainer.model_validate_json(text)
        )
        assert reconstituted == wrapper


class TestBaselineTraceArtifactMissing:
    def _build(self, **overrides):
        defaults = dict(
            needed_artifact="page_errors_log",
            expected_artifact_path=Path(
                "/tmp/case/trace/page_errors.jsonl"
            ),
        )
        defaults.update(overrides)
        return BaselineTraceArtifactMissing(**defaults)

    def test_kind_literal(self):
        reason = self._build()
        assert reason.kind == (
            "baseline_trace_artifact_missing"
        )

    def test_needed_artifact_required(self):
        with pytest.raises(ValidationError):
            BaselineTraceArtifactMissing(
                expected_artifact_path=Path("/tmp/x"),
            )  # type: ignore[call-arg]

    def test_expected_artifact_path_required(self):
        with pytest.raises(ValidationError):
            BaselineTraceArtifactMissing(
                needed_artifact="page_errors_log",
            )  # type: ignore[call-arg]

    def test_unknown_artifact_rejected(self):
        with pytest.raises(ValidationError):
            self._build(needed_artifact="screenshots")

    def test_default_recovery_present(self):
        reason = self._build()
        assert "open_agent.py" in reason.recovery
        assert "expected_artifact_path" in reason.recovery
        assert "To proceed:" in reason.recovery

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            self._build(extra="nope")

    def test_frozen(self):
        reason = self._build()
        with pytest.raises(ValidationError):
            reason.needed_artifact = "page_errors_log"  # type: ignore[misc]


class TestBaselineTraceLogMalformed:
    def _build(self, **overrides):
        defaults = dict(
            log_path=Path(
                "/tmp/case/trace/page_errors.jsonl"
            ),
            line_number=2,
            parse_error="invalid JSON (Expecting value)",
        )
        defaults.update(overrides)
        return BaselineTraceLogMalformed(**defaults)

    def test_kind_literal(self):
        reason = self._build()
        assert reason.kind == (
            "baseline_trace_log_malformed"
        )

    def test_log_path_required(self):
        with pytest.raises(ValidationError):
            BaselineTraceLogMalformed(
                line_number=1,
                parse_error="x",
            )  # type: ignore[call-arg]

    def test_parse_error_required(self):
        with pytest.raises(ValidationError):
            BaselineTraceLogMalformed(
                log_path=Path("/tmp/x"),
                line_number=1,
            )  # type: ignore[call-arg]

    def test_parse_error_min_length(self):
        with pytest.raises(ValidationError):
            self._build(parse_error="")

    def test_line_number_optional(self):
        reason = self._build(line_number=None)
        assert reason.line_number is None

    def test_line_number_minimum(self):
        with pytest.raises(ValidationError):
            self._build(line_number=0)

    def test_default_recovery_present(self):
        reason = self._build()
        assert "log_path" in reason.recovery
        assert "open_agent.py" in reason.recovery
        assert "To proceed:" in reason.recovery

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            self._build(extra="nope")

    def test_frozen(self):
        reason = self._build()
        with pytest.raises(ValidationError):
            reason.parse_error = "different"  # type: ignore[misc]

    def test_from_error_classmethod_jsonl(self):
        error = StructuredLogParseError(
            path=Path("/tmp/case/trace/page_errors.jsonl"),
            line_number=4,
            parse_error="schema violation",
        )
        reason = BaselineTraceLogMalformed.from_error(error)
        assert reason.log_path == error.path
        assert reason.line_number == 4
        assert reason.parse_error == "schema violation"
