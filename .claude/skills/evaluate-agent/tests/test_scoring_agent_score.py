"""
Tests for the agent_score composer and the AgentRollup / AgentScore schemas.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evaluate_agent.scoring import (
    AgentRollup,
    AgentScore,
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionKindRollup,
    AssertionPassed,
    AssertionTargetRollup,
    CaseOutcomeRollup,
    CaseScore,
    DOMSnapshotUnavailable,
    ObservabilitySourceMissing,
    score_agent,
)
from pydantic import ValidationError


def _passed(
    kind,
    target=None,
    *,
    artifact_path="/tmp/agent_score/evidence.html",
    detail=None,
):
    return AssertionPassed(
        assertion_kind=kind,
        target=target,
        evidence=AssertionEvidence(
            artifact_path=Path(artifact_path).resolve(),
            detail=detail,
        ),
    )


def _failed(
    kind,
    target=None,
    *,
    expected="needle",
    observed="haystack",
    artifact_path="/tmp/agent_score/evidence.html",
):
    return AssertionFailed(
        assertion_kind=kind,
        target=target,
        expected=expected,
        observed=observed,
        evidence=AssertionEvidence(
            artifact_path=Path(artifact_path).resolve(),
        ),
    )


def _obs_missing(
    kind, target=None, *, needed="tool_call_log"
):
    return AssertionInconclusive(
        assertion_kind=kind,
        target=target,
        reason=ObservabilitySourceMissing(
            needed_evidence=needed,
            expected_artifact_path=Path(
                "/tmp/agent_score/case_x/trace/"
                f"observability/{needed}.jsonl"
            ),
        ),
    )


def _dom_missing(
    kind,
    target=None,
    *,
    expected_dir="/tmp/agent_score/case_x/trace/dom",
):
    return AssertionInconclusive(
        assertion_kind=kind,
        target=target,
        reason=DOMSnapshotUnavailable(
            expected_artifact_dir=Path(
                expected_dir
            ).resolve(),
        ),
    )


def _case(
    case_id,
    *outcomes,
    case_dir="/tmp/agent_score/cases",
):
    return CaseScore(
        case_id=case_id,
        case_dir=(Path(case_dir) / case_id).resolve(),
        outcomes=outcomes,
    )


def _compose(
    *case_scores,
    agent_name="demo-agent",
    run_id="20260425T173000Z",
    runs_root="/tmp/agent_score/runs",
    manifest_path="/tmp/agent_score/agent.yaml",
):
    return score_agent(
        case_scores=case_scores,
        agent_name=agent_name,
        run_id=run_id,
        runs_root=Path(runs_root).resolve(),
        manifest_path=Path(manifest_path).resolve(),
    )


class TestAssertionKindRollupSchema:
    def test_counts_must_partition_total(self) -> None:
        with pytest.raises(
            ValidationError, match="partition total"
        ):
            AssertionKindRollup(
                assertion_kind="must_call",
                total=5,
                passed=1,
                failed=1,
                inconclusive=1,
            )

    def test_zero_counts_partition_zero_total(
        self,
    ) -> None:
        rollup = AssertionKindRollup(
            assertion_kind="max_steps",
            total=0,
            passed=0,
            failed=0,
            inconclusive=0,
        )
        assert rollup.total == 0

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssertionKindRollup(
                assertion_kind="must_call",
                total=1,
                passed=1,
                failed=0,
                inconclusive=0,
                extra="nope",
            )

    def test_frozen(self) -> None:
        rollup = AssertionKindRollup(
            assertion_kind="must_call",
            total=0,
            passed=0,
            failed=0,
            inconclusive=0,
        )
        with pytest.raises(ValidationError):
            rollup.total = 1  # type: ignore[misc]

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssertionKindRollup(
                assertion_kind="must_call",
                total=-1,
                passed=0,
                failed=0,
                inconclusive=0,
            )

    def test_assertion_kind_literal_enforced(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            AssertionKindRollup(
                assertion_kind="not_a_real_kind",
                total=0,
                passed=0,
                failed=0,
                inconclusive=0,
            )


class TestAssertionTargetRollupSchema:
    def test_counts_must_partition_total(self) -> None:
        with pytest.raises(
            ValidationError, match="partition total"
        ):
            AssertionTargetRollup(
                assertion_kind="must_call",
                target="search_flights",
                total=2,
                passed=2,
                failed=2,
                inconclusive=0,
            )

    def test_target_min_length_one(self) -> None:
        with pytest.raises(ValidationError):
            AssertionTargetRollup(
                assertion_kind="must_call",
                target="",
                total=0,
                passed=0,
                failed=0,
                inconclusive=0,
            )

    def test_targeted_kind_literal_enforced(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            AssertionTargetRollup(
                assertion_kind="final_response_contains",
                target="anything",
                total=0,
                passed=0,
                failed=0,
                inconclusive=0,
            )

    def test_max_steps_rejected_as_targeted_kind(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            AssertionTargetRollup(
                assertion_kind="max_steps",
                target="anything",
                total=0,
                passed=0,
                failed=0,
                inconclusive=0,
            )

    def test_must_call_accepted(self) -> None:
        rollup = AssertionTargetRollup(
            assertion_kind="must_call",
            target="search",
            total=2,
            passed=1,
            failed=1,
            inconclusive=0,
        )
        assert rollup.target == "search"

    def test_must_route_to_accepted(self) -> None:
        rollup = AssertionTargetRollup(
            assertion_kind="must_route_to",
            target="booking_subagent",
            total=1,
            passed=0,
            failed=0,
            inconclusive=1,
        )
        assert rollup.assertion_kind == "must_route_to"

    def test_frozen(self) -> None:
        rollup = AssertionTargetRollup(
            assertion_kind="must_call",
            target="search",
            total=0,
            passed=0,
            failed=0,
            inconclusive=0,
        )
        with pytest.raises(ValidationError):
            rollup.target = "other"  # type: ignore[misc]


class TestCaseOutcomeRollupSchema:
    def test_subcategory_capped_by_total(self) -> None:
        with pytest.raises(
            ValidationError,
            match="exceeds total",
        ):
            CaseOutcomeRollup(
                total=2,
                fully_passed=3,
                with_any_failure=0,
                with_any_inconclusive=0,
                with_no_assertions=0,
            )

    def test_fully_passed_and_no_assertions_mutex(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="mutually exclusive",
        ):
            CaseOutcomeRollup(
                total=3,
                fully_passed=2,
                with_any_failure=0,
                with_any_inconclusive=0,
                with_no_assertions=2,
            )

    def test_overlap_between_failure_and_inconclusive_allowed(
        self,
    ) -> None:
        rollup = CaseOutcomeRollup(
            total=3,
            fully_passed=0,
            with_any_failure=3,
            with_any_inconclusive=3,
            with_no_assertions=0,
        )
        assert rollup.with_any_failure == 3
        assert rollup.with_any_inconclusive == 3

    def test_zero_total_zero_categories(self) -> None:
        rollup = CaseOutcomeRollup(
            total=0,
            fully_passed=0,
            with_any_failure=0,
            with_any_inconclusive=0,
            with_no_assertions=0,
        )
        assert rollup.total == 0


class TestAgentRollupSchema:
    def test_top_level_counts_must_partition_total(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="partition total_assertions",
        ):
            AgentRollup(
                total_assertions=5,
                passed=1,
                failed=1,
                inconclusive=1,
                by_assertion_kind=(),
                by_target=(),
                cases=CaseOutcomeRollup(
                    total=0,
                    fully_passed=0,
                    with_any_failure=0,
                    with_any_inconclusive=0,
                    with_no_assertions=0,
                ),
            )

    def test_by_assertion_kind_sums_match_top_level(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="by_assertion_kind totals",
        ):
            AgentRollup(
                total_assertions=2,
                passed=2,
                failed=0,
                inconclusive=0,
                by_assertion_kind=(
                    AssertionKindRollup(
                        assertion_kind="must_call",
                        total=1,
                        passed=1,
                        failed=0,
                        inconclusive=0,
                    ),
                ),
                by_target=(
                    AssertionTargetRollup(
                        assertion_kind="must_call",
                        target="search",
                        total=1,
                        passed=1,
                        failed=0,
                        inconclusive=0,
                    ),
                ),
                cases=CaseOutcomeRollup(
                    total=2,
                    fully_passed=2,
                    with_any_failure=0,
                    with_any_inconclusive=0,
                    with_no_assertions=0,
                ),
            )

    def test_by_target_sums_match_kind_total(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="by_target totals",
        ):
            AgentRollup(
                total_assertions=3,
                passed=3,
                failed=0,
                inconclusive=0,
                by_assertion_kind=(
                    AssertionKindRollup(
                        assertion_kind="must_call",
                        total=3,
                        passed=3,
                        failed=0,
                        inconclusive=0,
                    ),
                ),
                by_target=(
                    AssertionTargetRollup(
                        assertion_kind="must_call",
                        target="search",
                        total=2,
                        passed=2,
                        failed=0,
                        inconclusive=0,
                    ),
                ),
                cases=CaseOutcomeRollup(
                    total=3,
                    fully_passed=3,
                    with_any_failure=0,
                    with_any_inconclusive=0,
                    with_no_assertions=0,
                ),
            )

    def test_by_target_for_undeclared_kind_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match=("by_target references assertion_kind"),
        ):
            AgentRollup(
                total_assertions=0,
                passed=0,
                failed=0,
                inconclusive=0,
                by_assertion_kind=(),
                by_target=(
                    AssertionTargetRollup(
                        assertion_kind="must_call",
                        target="orphan",
                        total=0,
                        passed=0,
                        failed=0,
                        inconclusive=0,
                    ),
                ),
                cases=CaseOutcomeRollup(
                    total=0,
                    fully_passed=0,
                    with_any_failure=0,
                    with_any_inconclusive=0,
                    with_no_assertions=0,
                ),
            )

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentRollup(
                total_assertions=0,
                passed=0,
                failed=0,
                inconclusive=0,
                by_assertion_kind=(),
                by_target=(),
                cases=CaseOutcomeRollup(
                    total=0,
                    fully_passed=0,
                    with_any_failure=0,
                    with_any_inconclusive=0,
                    with_no_assertions=0,
                ),
                extra="nope",
            )


class TestAgentScoreSchema:
    def test_case_scores_min_length_one(self) -> None:
        with pytest.raises(ValidationError):
            score_agent(
                case_scores=(),
                agent_name="demo-agent",
                run_id="20260425T173000Z",
                runs_root=Path("/tmp/x").resolve(),
                manifest_path=Path(
                    "/tmp/x/agent.yaml"
                ).resolve(),
            )

    def test_run_id_format_validated(self) -> None:
        with pytest.raises(
            ValidationError, match="YYYYMMDDTHHMMSSZ"
        ):
            _compose(
                _case("a", _passed("max_steps")),
                run_id="not-a-run-id",
            )

    def test_run_id_calendar_invalid_rejected(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError, match="YYYYMMDDTHHMMSSZ"
        ):
            _compose(
                _case("a", _passed("max_steps")),
                run_id="20260230T000000Z",
            )

    def test_duplicate_case_ids_rejected(self) -> None:
        with pytest.raises(
            ValidationError,
            match="duplicate case ids",
        ):
            _compose(
                _case("a", _passed("max_steps")),
                _case("a", _passed("max_steps")),
            )

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentScore(
                agent_name="demo-agent",
                run_id="20260425T173000Z",
                runs_root=Path("/tmp/x").resolve(),
                manifest_path=Path(
                    "/tmp/x/agent.yaml"
                ).resolve(),
                case_scores=(
                    _case("a", _passed("max_steps")),
                ),
                rollup=_compose(
                    _case("a", _passed("max_steps"))
                ).rollup,
                extra="nope",  # type: ignore[call-arg]
            )

    def test_frozen(self) -> None:
        score = _compose(_case("a", _passed("max_steps")))
        with pytest.raises(ValidationError):
            score.agent_name = (  # type: ignore[misc]
                "other"
            )


class TestComposeRollupTopLevel:
    def test_single_case_all_passed(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
                _passed("max_steps"),
            )
        )
        assert score.rollup.total_assertions == 2
        assert score.rollup.passed == 2
        assert score.rollup.failed == 0
        assert score.rollup.inconclusive == 0

    def test_mixed_pass_fail_inconclusive(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
                _failed(
                    "max_steps", expected="3", observed="5"
                ),
                _obs_missing("must_call", "search"),
            )
        )
        assert score.rollup.total_assertions == 3
        assert score.rollup.passed == 1
        assert score.rollup.failed == 1
        assert score.rollup.inconclusive == 1

    def test_multi_case_aggregated_top_level(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
                _passed("max_steps"),
            ),
            _case(
                "beta",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
                _obs_missing("must_route_to", "router"),
            ),
            _case(
                "gamma",
                _obs_missing("must_call", "search"),
                _obs_missing("must_call", "filter"),
            ),
        )
        assert score.rollup.total_assertions == 6
        assert score.rollup.passed == 2
        assert score.rollup.failed == 1
        assert score.rollup.inconclusive == 3


class TestComposeRollupByAssertionKind:
    def test_one_row_per_declared_kind(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
                _passed("max_steps"),
                _obs_missing("must_call", "search"),
            )
        )
        kinds = tuple(
            row.assertion_kind
            for row in score.rollup.by_assertion_kind
        )
        assert set(kinds) == {
            "final_response_contains",
            "must_call",
            "max_steps",
        }

    def test_kinds_omitted_when_zero_outcomes(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("max_steps"),
            )
        )
        kinds = tuple(
            row.assertion_kind
            for row in score.rollup.by_assertion_kind
        )
        assert kinds == ("max_steps",)

    def test_kinds_emitted_in_schema_order(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("max_steps"),
                _obs_missing("must_route_to", "router"),
                _obs_missing("must_call", "search"),
                _obs_missing("must_not_call", "danger"),
                _passed("final_response_contains"),
            )
        )
        assert tuple(
            row.assertion_kind
            for row in score.rollup.by_assertion_kind
        ) == (
            "final_response_contains",
            "must_call",
            "must_not_call",
            "must_route_to",
            "max_steps",
        )

    def test_per_kind_outcome_counts(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("must_call", "search"),
                _failed("must_call", "filter"),
                _obs_missing("must_call", "rank"),
            )
        )
        (must_call,) = (
            row
            for row in score.rollup.by_assertion_kind
            if row.assertion_kind == "must_call"
        )
        assert must_call.total == 3
        assert must_call.passed == 1
        assert must_call.failed == 1
        assert must_call.inconclusive == 1


class TestComposeRollupByTarget:
    def test_one_row_per_kind_target_pair(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _obs_missing("must_call", "search"),
                _obs_missing("must_not_call", "search"),
            )
        )
        keys = tuple(
            (row.assertion_kind, row.target)
            for row in score.rollup.by_target
        )
        assert keys == (
            ("must_call", "search"),
            ("must_not_call", "search"),
        )

    def test_same_target_aggregates_across_cases(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("must_call", "search"),
            ),
            _case(
                "beta",
                _failed("must_call", "search"),
            ),
            _case(
                "gamma",
                _obs_missing("must_call", "search"),
            ),
        )
        (row,) = score.rollup.by_target
        assert row.assertion_kind == "must_call"
        assert row.target == "search"
        assert row.total == 3
        assert row.passed == 1
        assert row.failed == 1
        assert row.inconclusive == 1

    def test_targets_sorted_within_kind_lex(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _obs_missing("must_call", "zeta"),
                _obs_missing("must_call", "alpha"),
                _obs_missing("must_call", "mid"),
            )
        )
        targets = tuple(
            row.target for row in score.rollup.by_target
        )
        assert targets == ("alpha", "mid", "zeta")

    def test_kinds_sorted_in_schema_order(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _obs_missing("must_route_to", "router"),
                _obs_missing("must_not_call", "danger"),
                _obs_missing("must_call", "search"),
            )
        )
        kinds = tuple(
            row.assertion_kind
            for row in score.rollup.by_target
        )
        assert kinds == (
            "must_call",
            "must_not_call",
            "must_route_to",
        )

    def test_non_targeted_kinds_absent_from_by_target(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
                _passed("max_steps"),
            )
        )
        assert score.rollup.by_target == ()


class TestComposeRollupCaseLevel:
    def test_total_cases_counted(self) -> None:
        score = _compose(
            _case("a", _passed("max_steps")),
            _case("b", _passed("max_steps")),
            _case("c", _passed("max_steps")),
        )
        assert score.rollup.cases.total == 3

    def test_fully_passed_requires_no_failure_or_inconclusive(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
                _passed("max_steps"),
            ),
            _case(
                "beta",
                _passed("final_response_contains"),
                _failed(
                    "max_steps",
                    expected="3",
                    observed="5",
                ),
            ),
            _case(
                "gamma",
                _passed("final_response_contains"),
                _obs_missing("must_call", "search"),
            ),
        )
        assert score.rollup.cases.fully_passed == 1

    def test_with_any_failure_counts_failed_cases(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
            ),
            _case(
                "beta",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
            ),
            _case(
                "gamma",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
                _obs_missing("must_call", "search"),
            ),
        )
        assert score.rollup.cases.with_any_failure == 2

    def test_with_any_inconclusive_counts_inconclusive_cases(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
            ),
            _case(
                "beta",
                _obs_missing("must_call", "search"),
            ),
            _case(
                "gamma",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
                _obs_missing("must_call", "search"),
            ),
        )
        assert score.rollup.cases.with_any_inconclusive == 2

    def test_failure_and_inconclusive_overlap(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
                _obs_missing("must_call", "search"),
            )
        )
        assert score.rollup.cases.with_any_failure == 1
        assert score.rollup.cases.with_any_inconclusive == 1

    def test_with_no_assertions_counts_empty_cases(
        self,
    ) -> None:
        score = _compose(
            _case("alpha"),
            _case("beta", _passed("max_steps")),
            _case("gamma"),
        )
        assert score.rollup.cases.with_no_assertions == 2

    def test_no_assertions_case_does_not_count_as_fully_passed(
        self,
    ) -> None:
        score = _compose(
            _case("alpha"),
            _case("beta", _passed("max_steps")),
        )
        assert score.rollup.cases.fully_passed == 1
        assert score.rollup.cases.with_no_assertions == 1


class TestComposeRollupDOMSnapshotInconclusive:
    def test_dom_snapshot_inconclusive_aggregated(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _dom_missing("final_response_contains"),
            )
        )
        (kind_row,) = score.rollup.by_assertion_kind
        assert (
            kind_row.assertion_kind
            == "final_response_contains"
        )
        assert kind_row.total == 1
        assert kind_row.inconclusive == 1


class TestAgentScoreJSONRoundTrip:
    def test_round_trip_preserves_equality(self) -> None:
        score = _compose(
            _case(
                "alpha",
                _passed("final_response_contains"),
                _passed("max_steps"),
            ),
            _case(
                "beta",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
                _obs_missing("must_call", "search"),
            ),
        )
        dumped = score.model_dump_json()
        reconstructed = AgentScore.model_validate_json(
            dumped
        )
        assert reconstructed == score

    def test_top_level_keys_are_minimal(self) -> None:
        score = _compose(
            _case("alpha", _passed("max_steps"))
        )
        payload = json.loads(score.model_dump_json())
        assert set(payload.keys()) == {
            "agent_name",
            "run_id",
            "runs_root",
            "manifest_path",
            "case_scores",
            "rollup",
        }

    def test_path_fields_serialize_as_strings(
        self,
    ) -> None:
        score = _compose(
            _case("alpha", _passed("max_steps"))
        )
        payload = json.loads(score.model_dump_json())
        assert isinstance(payload["runs_root"], str)
        assert isinstance(payload["manifest_path"], str)

    def test_rollup_has_all_aggregation_dimensions(
        self,
    ) -> None:
        score = _compose(
            _case(
                "alpha",
                _obs_missing("must_call", "search"),
            )
        )
        payload = json.loads(score.model_dump_json())[
            "rollup"
        ]
        assert set(payload.keys()) == {
            "total_assertions",
            "passed",
            "failed",
            "inconclusive",
            "by_assertion_kind",
            "by_target",
            "cases",
        }


class TestComposeRollupDeterminism:
    def test_identical_inputs_produce_identical_output(
        self,
    ) -> None:
        a = _compose(
            _case(
                "alpha",
                _obs_missing("must_call", "search"),
                _passed("final_response_contains"),
            ),
            _case(
                "beta",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
            ),
        )
        b = _compose(
            _case(
                "alpha",
                _obs_missing("must_call", "search"),
                _passed("final_response_contains"),
            ),
            _case(
                "beta",
                _failed(
                    "final_response_contains",
                    expected="x",
                    observed="y",
                ),
            ),
        )
        assert a == b
        assert a.model_dump_json() == b.model_dump_json()

    def test_case_order_preserved_in_dump(self) -> None:
        score = _compose(
            _case("delta", _passed("max_steps")),
            _case("alpha", _passed("max_steps")),
            _case("beta", _passed("max_steps")),
        )
        case_ids = tuple(
            cs.case_id for cs in score.case_scores
        )
        assert case_ids == ("delta", "alpha", "beta")
