"""
Tests for the four assertion evaluators that require observability evidence.
"""

from __future__ import annotations

from evaluate_agent.scoring.inconclusive_reasons import (
    ObservabilitySourceMissing,
)
from evaluate_agent.scoring.max_steps import (
    evaluate_max_steps,
)
from evaluate_agent.scoring.must_call import (
    evaluate_must_call,
)
from evaluate_agent.scoring.must_not_call import (
    evaluate_must_not_call,
)
from evaluate_agent.scoring.must_route_to import (
    evaluate_must_route_to,
)
from evaluate_agent.scoring.outcomes import (
    AssertionInconclusive,
)


class TestEvaluateMustCall:
    def test_returns_inconclusive(self):
        outcome = evaluate_must_call("lookup_pix")
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "must_call"
        assert outcome.target == "lookup_pix"

    def test_reason_names_tool_call_log(self):
        outcome = evaluate_must_call("transfer")
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence
            == "tool_call_log"
        )


class TestEvaluateMustNotCall:
    def test_returns_inconclusive(self):
        outcome = evaluate_must_not_call("delete_account")
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "must_not_call"
        assert outcome.target == "delete_account"

    def test_reason_names_tool_call_log(self):
        outcome = evaluate_must_not_call("transfer")
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence
            == "tool_call_log"
        )


class TestEvaluateMustRouteTo:
    def test_returns_inconclusive(self):
        outcome = evaluate_must_route_to(
            "billing_specialist"
        )
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "must_route_to"
        assert outcome.target == "billing_specialist"

    def test_reason_names_routing_log(self):
        outcome = evaluate_must_route_to("tier2_support")
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence
            == "routing_decision_log"
        )


class TestEvaluateMaxSteps:
    def test_returns_inconclusive(self):
        outcome = evaluate_max_steps(5)
        assert isinstance(outcome, AssertionInconclusive)
        assert outcome.assertion_kind == "max_steps"

    def test_target_is_none(self):
        outcome = evaluate_max_steps(20)
        assert outcome.target is None

    def test_reason_names_step_count(self):
        outcome = evaluate_max_steps(5)
        assert isinstance(
            outcome.reason, ObservabilitySourceMissing
        )
        assert (
            outcome.reason.needed_evidence == "step_count"
        )
