"""
Tests for the discriminated InconclusiveReason union.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.scoring.inconclusive_reasons import (
    DOMSnapshotUnavailable,
    InconclusiveReason,
    ObservabilitySourceMissing,
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
    def test_kind_literal(self):
        reason = ObservabilitySourceMissing(
            needed_evidence="tool_call_log",
        )
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
        reason = ObservabilitySourceMissing(
            needed_evidence=evidence,
        )
        assert reason.needed_evidence == evidence

    def test_unknown_evidence_rejected(self):
        with pytest.raises(ValidationError):
            ObservabilitySourceMissing(
                needed_evidence="vibes",  # type: ignore[arg-type]
            )

    def test_default_recovery_present(self):
        reason = ObservabilitySourceMissing(
            needed_evidence="tool_call_log",
        )
        assert "manifest.observability" in reason.recovery
        assert "To proceed:" in reason.recovery

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            ObservabilitySourceMissing(
                needed_evidence="tool_call_log",
                extra="nope",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        reason = ObservabilitySourceMissing(
            needed_evidence="step_count",
        )
        with pytest.raises(ValidationError):
            reason.needed_evidence = (  # type: ignore[misc]
                "tool_call_log"
            )


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
            }
        )
        assert isinstance(
            reason, ObservabilitySourceMissing
        )

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
                needed_evidence=("routing_decision_log"),
            ),
        )
        text = wrapper.model_dump_json()
        reconstituted = (
            _ReasonContainer.model_validate_json(text)
        )
        assert reconstituted == wrapper
