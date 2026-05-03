"""
Failure-mode tests for the tool-call-grounded evaluators (must_call, must_not_call, must_call_exactly, must_call_with_args, must_call_in_order).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import write_tool_calls
from evaluate_agent.artifact_layout import (
    OBSERVABILITY_SUBDIR,
    TOOL_CALL_LOG_FILENAME,
    TRACE_SUBDIR,
)
from evaluate_agent.manifest.schema import CallSpec
from evaluate_agent.scoring.evaluators import (
    evaluate_must_call,
    evaluate_must_call_exactly,
    evaluate_must_call_in_order,
    evaluate_must_call_with_args,
    evaluate_must_not_call,
)
from evaluate_agent.scoring.outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    DOMSnapshotUnavailable,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)


def test_must_call_inconclusive_when_log_absent(
    case_dir: Path,
) -> None:
    # Distinct from "tool not called" — the assertion cannot be
    # evaluated at all. Operators reading the report should see
    # the recovery procedure for wiring observability, not a
    # phantom failed outcome.
    outcome = evaluate_must_call("lookup", case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, ObservabilitySourceMissing
    )
    assert outcome.reason.needed_evidence == "tool_call_log"


def test_must_call_inconclusive_when_log_malformed(
    case_dir: Path,
) -> None:
    # Bad JSON in the log surfaces as ObservabilityLogMalformed
    # with the offending line number — the operator can fix
    # the file in one round trip.
    path = (
        case_dir
        / TRACE_SUBDIR
        / OBSERVABILITY_SUBDIR
        / TOOL_CALL_LOG_FILENAME
    )
    path.parent.mkdir(parents=True)
    path.write_text("{not json}\n", encoding="utf-8")
    outcome = evaluate_must_call("lookup", case_dir)
    assert isinstance(outcome, AssertionInconclusive)
    assert isinstance(
        outcome.reason, ObservabilityLogMalformed
    )
    assert outcome.reason.line_number == 1


def test_must_call_passes_with_first_match_citation(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "other", "span_id": "s1"},
            {"tool_name": "lookup", "span_id": "s2"},
            {"tool_name": "lookup", "span_id": "s3"},
        ],
    )
    outcome = evaluate_must_call("lookup", case_dir)
    assert isinstance(outcome, AssertionPassed)
    assert "line 2" in outcome.evidence.detail
    assert "s2" in outcome.evidence.detail


def test_must_call_fails_with_observed_tool_summary(
    case_dir: Path,
) -> None:
    # Failure detail must surface the observed-but-not-matched
    # tools so the operator sees the bug instantly: "I asked
    # for `lookup` and the agent called `unrelated` instead."
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "unrelated_one", "span_id": "s1"},
            {"tool_name": "unrelated_two", "span_id": "s2"},
        ],
    )
    outcome = evaluate_must_call("lookup", case_dir)
    assert isinstance(outcome, AssertionFailed)
    assert (
        outcome.observed == "unrelated_one, unrelated_two"
    )


def test_must_not_call_fails_at_first_forbidden_invocation(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "ok_one", "span_id": "s1"},
            {"tool_name": "forbidden", "span_id": "s2"},
            {"tool_name": "ok_two", "span_id": "s3"},
        ],
    )
    outcome = evaluate_must_not_call("forbidden", case_dir)
    assert isinstance(outcome, AssertionFailed)
    assert "line 2" in outcome.evidence.detail
    assert "s2" in outcome.evidence.detail


def test_must_not_call_passes_when_tool_absent(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "ok", "span_id": "s1"},
        ],
    )
    outcome = evaluate_must_not_call("forbidden", case_dir)
    assert isinstance(outcome, AssertionPassed)


def test_must_call_exactly_fails_on_redundant_invocation(
    case_dir: Path,
) -> None:
    # Use case: a two-employee query should produce exactly two
    # lookups. A redundant third call signals an agent bug that
    # must_call alone cannot surface.
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "lookup", "span_id": "s1"},
            {"tool_name": "lookup", "span_id": "s2"},
            {"tool_name": "lookup", "span_id": "s3"},
        ],
    )
    outcome = evaluate_must_call_exactly(
        "lookup", required_count=2, case_dir=case_dir
    )
    assert isinstance(outcome, AssertionFailed)
    assert outcome.expected == "exactly 2 call(s)"
    assert outcome.observed == "3 call(s)"


def test_must_call_exactly_passes_with_every_line_cited(
    case_dir: Path,
) -> None:
    # The detail must enumerate EVERY matching line. Operators
    # rely on this when must_call_exactly's value is the count
    # itself — a single line citation would hide the rest.
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "lookup", "span_id": "s1"},
            {"tool_name": "other", "span_id": "s2"},
            {"tool_name": "lookup", "span_id": "s3"},
        ],
    )
    outcome = evaluate_must_call_exactly(
        "lookup", required_count=2, case_dir=case_dir
    )
    assert isinstance(outcome, AssertionPassed)
    detail = outcome.evidence.detail
    assert "1" in detail and "3" in detail


def test_must_call_with_args_passes_on_deep_subset_match(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {
                "tool_name": "transfer",
                "span_id": "s1",
                "arguments": {
                    "amount": 100,
                    "to": "alex",
                    "extra": "ignored",
                },
            }
        ],
    )
    spec = CallSpec(
        tool_name="transfer", args={"amount": 100}
    )
    outcome = evaluate_must_call_with_args(spec, case_dir)
    assert isinstance(outcome, AssertionPassed)


def test_must_call_with_args_recurses_into_nested_mapping(
    case_dir: Path,
) -> None:
    # Nested args are the realistic shape: {"user": {"id": 7}}.
    # Subset matching must recurse so a partial nested expectation
    # passes when the captured nested mapping is a superset.
    write_tool_calls(
        case_dir,
        [
            {
                "tool_name": "lookup",
                "span_id": "s",
                "arguments": {
                    "user": {"id": 7, "tenant": "T"},
                    "trace_id": "abc",
                },
            }
        ],
    )
    spec = CallSpec(
        tool_name="lookup", args={"user": {"id": 7}}
    )
    outcome = evaluate_must_call_with_args(spec, case_dir)
    assert isinstance(outcome, AssertionPassed)


def test_must_call_with_args_fails_when_value_differs(
    case_dir: Path,
) -> None:
    # The canonical bug class: right tool, wrong arg value
    # (e.g. transfer(amount=10000) instead of 100). must_call
    # alone would have passed; must_call_with_args must fail.
    write_tool_calls(
        case_dir,
        [
            {
                "tool_name": "transfer",
                "span_id": "s",
                "arguments": {"amount": 10000},
            }
        ],
    )
    spec = CallSpec(
        tool_name="transfer", args={"amount": 100}
    )
    outcome = evaluate_must_call_with_args(spec, case_dir)
    assert isinstance(outcome, AssertionFailed)


def test_must_call_with_args_skips_entries_without_arguments(
    case_dir: Path,
) -> None:
    # A captured tool_call without arguments cannot satisfy an
    # args-shape assertion. Treating it as a non-match (rather
    # than a match) keeps the assertion meaningful when the
    # fetcher emits a record without an `arguments` key.
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "lookup", "span_id": "s"},
        ],
    )
    spec = CallSpec(
        tool_name="lookup", args={"alias": "alex"}
    )
    outcome = evaluate_must_call_with_args(spec, case_dir)
    assert isinstance(outcome, AssertionFailed)


def test_must_call_with_args_min_count_is_inclusive_floor(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {
                "tool_name": "lookup",
                "span_id": "s1",
                "arguments": {"alias": "alex"},
            },
            {
                "tool_name": "lookup",
                "span_id": "s2",
                "arguments": {"alias": "alex"},
            },
        ],
    )
    spec = CallSpec(
        tool_name="lookup",
        args={"alias": "alex"},
        min_count=2,
    )
    outcome = evaluate_must_call_with_args(spec, case_dir)
    assert isinstance(outcome, AssertionPassed)


def test_must_call_with_args_min_count_short_fails(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {
                "tool_name": "lookup",
                "span_id": "s1",
                "arguments": {"alias": "alex"},
            },
        ],
    )
    spec = CallSpec(
        tool_name="lookup",
        args={"alias": "alex"},
        min_count=2,
    )
    outcome = evaluate_must_call_with_args(spec, case_dir)
    assert isinstance(outcome, AssertionFailed)
    assert ">= 2" in outcome.expected


def test_must_call_in_order_subsequence_allows_intervening_calls(
    case_dir: Path,
) -> None:
    # Non-strict subsequence: the declared order must hold, but
    # other calls between are allowed. Use case: lookup must
    # precede list_paid_leave_days, intervening telemetry call
    # is fine.
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "lookup", "span_id": "s1"},
            {"tool_name": "telemetry", "span_id": "s2"},
            {
                "tool_name": "list_paid_leave_days",
                "span_id": "s3",
            },
        ],
    )
    outcome = evaluate_must_call_in_order(
        ["lookup", "list_paid_leave_days"], case_dir
    )
    assert isinstance(outcome, AssertionPassed)


def test_must_call_in_order_fails_when_order_inverted(
    case_dir: Path,
) -> None:
    # Order matters even when both names ARE present: an agent
    # that calls list_paid_leave_days before lookup has skipped
    # the dependency the assertion encodes.
    write_tool_calls(
        case_dir,
        [
            {
                "tool_name": "list_paid_leave_days",
                "span_id": "s1",
            },
            {"tool_name": "lookup", "span_id": "s2"},
        ],
    )
    outcome = evaluate_must_call_in_order(
        ["lookup", "list_paid_leave_days"], case_dir
    )
    assert isinstance(outcome, AssertionFailed)
    detail = outcome.evidence.detail
    assert "matched first 1" in detail
    assert "list_paid_leave_days" in detail


def test_must_call_in_order_fails_when_step_absent(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "lookup", "span_id": "s1"},
        ],
    )
    outcome = evaluate_must_call_in_order(
        ["lookup", "list_paid_leave_days"], case_dir
    )
    assert isinstance(outcome, AssertionFailed)


def test_must_call_in_order_passes_for_empty_sequence(
    case_dir: Path,
) -> None:
    # Vacuous truth: the empty subsequence is satisfied by any
    # log. The schema rejects an empty list at the manifest
    # layer, so this guards the evaluator against ever raising
    # on an upstream layering bug.
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "lookup", "span_id": "s1"},
        ],
    )
    outcome = evaluate_must_call_in_order([], case_dir)
    assert isinstance(outcome, AssertionPassed)
