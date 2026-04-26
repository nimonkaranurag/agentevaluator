"""
Tests for the assertion outcome union and evidence shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    DOMSnapshotUnavailable,
    ObservabilitySourceMissing,
)
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
)

_OUTCOME_ADAPTER = TypeAdapter(AssertionOutcome)


class _OutcomeContainer(BaseModel):
    item: AssertionOutcome = Field(...)


class TestAssertionEvidence:
    def test_artifact_path_required(self):
        with pytest.raises(ValidationError):
            AssertionEvidence()  # type: ignore[call-arg]

    def test_detail_optional(self):
        evidence = AssertionEvidence(
            artifact_path=Path("/tmp/x.html")
        )
        assert evidence.detail is None

    def test_detail_min_length(self):
        with pytest.raises(ValidationError):
            AssertionEvidence(
                artifact_path=Path("/tmp/x.html"),
                detail="",
            )

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            AssertionEvidence(
                artifact_path=Path("/tmp/x.html"),
                extra="nope",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        evidence = AssertionEvidence(
            artifact_path=Path("/tmp/x.html"),
            detail="ok",
        )
        with pytest.raises(ValidationError):
            evidence.detail = "modified"  # type: ignore[misc]


class TestAssertionPassed:
    def _build(self, **overrides) -> AssertionPassed:
        defaults = dict(
            assertion_kind="final_response_contains",
            evidence=AssertionEvidence(
                artifact_path=Path("/tmp/x.html"),
            ),
        )
        defaults.update(overrides)
        return AssertionPassed(**defaults)

    def test_outcome_literal_set(self):
        passed = self._build()
        assert passed.outcome == "passed"

    def test_assertion_kind_required(self):
        with pytest.raises(ValidationError):
            AssertionPassed(  # type: ignore[call-arg]
                evidence=AssertionEvidence(
                    artifact_path=Path("/tmp/x.html")
                ),
            )

    def test_invalid_assertion_kind_rejected(self):
        with pytest.raises(ValidationError):
            self._build(assertion_kind="not_a_real_kind")

    def test_no_uncaught_page_errors_kind_accepted(self):
        passed = self._build(
            assertion_kind="no_uncaught_page_errors"
        )
        assert (
            passed.assertion_kind
            == "no_uncaught_page_errors"
        )

    def test_target_optional(self):
        passed = self._build()
        assert passed.target is None

    def test_target_min_length(self):
        with pytest.raises(ValidationError):
            self._build(target="")

    def test_target_set(self):
        passed = self._build(
            assertion_kind="must_call",
            target="lookup_pix",
        )
        assert passed.target == "lookup_pix"

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            self._build(unexpected="nope")

    def test_frozen(self):
        passed = self._build()
        with pytest.raises(ValidationError):
            passed.target = "x"  # type: ignore[misc]


class TestAssertionFailed:
    def _build(self, **overrides) -> AssertionFailed:
        defaults = dict(
            assertion_kind="final_response_contains",
            expected="confirmed",
            observed="something else entirely",
            evidence=AssertionEvidence(
                artifact_path=Path("/tmp/x.html"),
            ),
        )
        defaults.update(overrides)
        return AssertionFailed(**defaults)

    def test_outcome_literal_set(self):
        failed = self._build()
        assert failed.outcome == "failed"

    def test_expected_required(self):
        with pytest.raises(ValidationError):
            AssertionFailed(  # type: ignore[call-arg]
                assertion_kind=("final_response_contains"),
                evidence=AssertionEvidence(
                    artifact_path=Path("/tmp/x.html")
                ),
            )

    def test_expected_min_length(self):
        with pytest.raises(ValidationError):
            self._build(expected="")

    def test_observed_optional(self):
        failed = self._build(observed=None)
        assert failed.observed is None

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            self._build(unexpected="nope")


class TestAssertionInconclusive:
    def _build(self, **overrides) -> AssertionInconclusive:
        defaults = dict(
            assertion_kind="final_response_contains",
            reason=DOMSnapshotUnavailable(
                expected_artifact_dir=Path(
                    "/tmp/case/trace/dom"
                ),
            ),
        )
        defaults.update(overrides)
        return AssertionInconclusive(**defaults)

    def test_outcome_literal_set(self):
        inconclusive = self._build()
        assert inconclusive.outcome == "inconclusive"

    def test_reason_dom_branch(self):
        inconclusive = self._build()
        assert isinstance(
            inconclusive.reason, DOMSnapshotUnavailable
        )

    def test_reason_observability_branch(self):
        inconclusive = self._build(
            assertion_kind="must_call",
            target="lookup_pix",
            reason=ObservabilitySourceMissing(
                needed_evidence="tool_call_log",
                expected_artifact_path=Path(
                    "/tmp/case/trace/observability/"
                    "tool_calls.jsonl"
                ),
            ),
        )
        assert isinstance(
            inconclusive.reason,
            ObservabilitySourceMissing,
        )

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            self._build(unexpected="nope")


class TestDiscriminatedUnion:
    def _passed(self) -> AssertionPassed:
        return AssertionPassed(
            assertion_kind="final_response_contains",
            evidence=AssertionEvidence(
                artifact_path=Path("/tmp/x.html"),
            ),
        )

    def _failed(self) -> AssertionFailed:
        return AssertionFailed(
            assertion_kind="final_response_contains",
            expected="confirmed",
            evidence=AssertionEvidence(
                artifact_path=Path("/tmp/x.html"),
            ),
        )

    def _inconclusive(
        self,
    ) -> AssertionInconclusive:
        return AssertionInconclusive(
            assertion_kind="must_call",
            target="lookup_pix",
            reason=ObservabilitySourceMissing(
                needed_evidence="tool_call_log",
                expected_artifact_path=Path(
                    "/tmp/case/trace/observability/"
                    "tool_calls.jsonl"
                ),
            ),
        )

    @pytest.mark.parametrize(
        "factory_name",
        ["_passed", "_failed", "_inconclusive"],
    )
    def test_round_trip_through_container(
        self, factory_name
    ):
        outcome = getattr(self, factory_name)()
        wrapper = _OutcomeContainer(item=outcome)
        json_text = wrapper.model_dump_json()
        reconstituted = (
            _OutcomeContainer.model_validate_json(json_text)
        )
        assert reconstituted == wrapper

    def test_validate_passed_via_adapter(self):
        outcome = _OUTCOME_ADAPTER.validate_python(
            {
                "outcome": "passed",
                "assertion_kind": (
                    "final_response_contains"
                ),
                "evidence": {
                    "artifact_path": "/tmp/x.html",
                },
            }
        )
        assert isinstance(outcome, AssertionPassed)

    def test_validate_failed_via_adapter(self):
        outcome = _OUTCOME_ADAPTER.validate_python(
            {
                "outcome": "failed",
                "assertion_kind": (
                    "final_response_contains"
                ),
                "expected": "confirmed",
                "evidence": {
                    "artifact_path": "/tmp/x.html",
                },
            }
        )
        assert isinstance(outcome, AssertionFailed)

    def test_validate_inconclusive_via_adapter(self):
        outcome = _OUTCOME_ADAPTER.validate_python(
            {
                "outcome": "inconclusive",
                "assertion_kind": "must_call",
                "target": "lookup_pix",
                "reason": {
                    "kind": (
                        "observability_source_missing"
                    ),
                    "needed_evidence": "tool_call_log",
                    "expected_artifact_path": (
                        "/tmp/case/trace/observability/"
                        "tool_calls.jsonl"
                    ),
                },
            }
        )
        assert isinstance(outcome, AssertionInconclusive)

    def test_unknown_outcome_rejected(self):
        with pytest.raises(ValidationError):
            _OUTCOME_ADAPTER.validate_python(
                {
                    "outcome": "winged_it",
                    "assertion_kind": (
                        "final_response_contains"
                    ),
                    "evidence": {
                        "artifact_path": "/tmp/x.html",
                    },
                }
            )
