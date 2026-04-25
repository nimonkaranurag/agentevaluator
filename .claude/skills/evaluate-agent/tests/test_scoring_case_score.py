"""
Tests for the case_score composer that aggregates per-assertion outcomes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evaluate_agent.manifest.schema import (
    Assertions,
    Case,
)
from evaluate_agent.scoring.case_score import (
    CaseScore,
    score_case,
)
from evaluate_agent.scoring.outcomes import (
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
)
from pydantic import ValidationError


def _seed_after_submit_dom(
    case_dir: Path,
    html: str,
    step_number: int = 2,
) -> Path:
    dom_dir = case_dir / "trace" / "dom"
    dom_dir.mkdir(parents=True, exist_ok=True)
    target = (
        dom_dir
        / f"step-{step_number:03d}-after_submit.html"
    )
    target.write_text(html, encoding="utf-8")
    return target


def _build_case(**assertion_overrides) -> Case:
    return Case(
        id="example_case",
        input="Hi there",
        assertions=Assertions(**assertion_overrides),
    )


class TestEmptyAssertions:
    def test_no_outcomes(self, tmp_path):
        score = score_case(
            case=_build_case(), case_dir=tmp_path
        )
        assert score.outcomes == ()
        assert score.total == 0
        assert score.passed == 0
        assert score.failed == 0
        assert score.inconclusive == 0


class TestPerAssertionDispatch:
    def test_final_response_contains_only_passed(
        self, tmp_path
    ):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body><p>booking confirmed"
            "</p></body></html>",
        )
        score = score_case(
            case=_build_case(
                final_response_contains="confirmed",
            ),
            case_dir=tmp_path,
        )
        assert len(score.outcomes) == 1
        assert isinstance(
            score.outcomes[0], AssertionPassed
        )

    def test_final_response_contains_only_failed(
        self, tmp_path
    ):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body><p>delayed</p></body></html>",
        )
        score = score_case(
            case=_build_case(
                final_response_contains="confirmed",
            ),
            case_dir=tmp_path,
        )
        assert len(score.outcomes) == 1
        assert isinstance(
            score.outcomes[0], AssertionFailed
        )

    def test_final_response_contains_only_inconclusive(
        self, tmp_path
    ):
        score = score_case(
            case=_build_case(
                final_response_contains="confirmed",
            ),
            case_dir=tmp_path,
        )
        assert len(score.outcomes) == 1
        assert isinstance(
            score.outcomes[0], AssertionInconclusive
        )

    def test_must_call_emits_one_outcome_per_tool(
        self, tmp_path
    ):
        score = score_case(
            case=_build_case(
                must_call=[
                    "lookup_pix",
                    "transfer",
                    "confirmar_pix",
                ],
            ),
            case_dir=tmp_path,
        )
        assert len(score.outcomes) == 3
        kinds = {
            outcome.assertion_kind
            for outcome in score.outcomes
        }
        assert kinds == {"must_call"}
        targets = [
            outcome.target for outcome in score.outcomes
        ]
        assert targets == [
            "lookup_pix",
            "transfer",
            "confirmar_pix",
        ]

    def test_must_not_call_emits_one_outcome_per_tool(
        self, tmp_path
    ):
        score = score_case(
            case=_build_case(
                must_not_call=[
                    "delete_account",
                    "wire_transfer",
                ],
            ),
            case_dir=tmp_path,
        )
        assert len(score.outcomes) == 2
        kinds = {
            outcome.assertion_kind
            for outcome in score.outcomes
        }
        assert kinds == {"must_not_call"}

    def test_must_route_to_emits_one_outcome(
        self, tmp_path
    ):
        score = score_case(
            case=_build_case(
                must_route_to="tier2_support",
            ),
            case_dir=tmp_path,
        )
        assert len(score.outcomes) == 1
        assert (
            score.outcomes[0].assertion_kind
            == "must_route_to"
        )

    def test_max_steps_emits_one_outcome(self, tmp_path):
        score = score_case(
            case=_build_case(max_steps=10),
            case_dir=tmp_path,
        )
        assert len(score.outcomes) == 1
        assert (
            score.outcomes[0].assertion_kind == "max_steps"
        )


class TestSchemaOrderPreserved:
    def test_outcomes_emitted_in_schema_order(
        self, tmp_path
    ):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body><p>done</p></body></html>",
        )
        score = score_case(
            case=_build_case(
                final_response_contains="done",
                must_call=["a", "b"],
                must_not_call=["c"],
                must_route_to="d",
                max_steps=5,
            ),
            case_dir=tmp_path,
        )
        kinds_in_order = [
            outcome.assertion_kind
            for outcome in score.outcomes
        ]
        assert kinds_in_order == [
            "final_response_contains",
            "must_call",
            "must_call",
            "must_not_call",
            "must_route_to",
            "max_steps",
        ]


class TestComputedSummary:
    def test_counts_aggregate(self, tmp_path):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body><p>delayed</p></body></html>",
        )
        score = score_case(
            case=_build_case(
                final_response_contains="confirmed",
                must_call=["a"],
                must_not_call=["b"],
                must_route_to="c",
                max_steps=5,
            ),
            case_dir=tmp_path,
        )
        assert score.total == 5
        assert score.failed == 1
        assert score.inconclusive == 4
        assert score.passed == 0

    def test_passed_count_when_substring_matches(
        self, tmp_path
    ):
        _seed_after_submit_dom(
            tmp_path,
            "<html><body>"
            "<p>Booking confirmed.</p>"
            "</body></html>",
        )
        score = score_case(
            case=_build_case(
                final_response_contains="confirmed",
            ),
            case_dir=tmp_path,
        )
        assert score.total == 1
        assert score.passed == 1
        assert score.failed == 0
        assert score.inconclusive == 0


class TestCaseScoreSchema:
    def _build_score(self, tmp_path) -> CaseScore:
        return score_case(
            case=_build_case(
                must_call=["lookup_pix"],
            ),
            case_dir=tmp_path,
        )

    def test_case_id_preserved(self, tmp_path):
        score = self._build_score(tmp_path)
        assert score.case_id == "example_case"

    def test_case_dir_preserved(self, tmp_path):
        score = self._build_score(tmp_path)
        assert score.case_dir == tmp_path

    def test_frozen_outcomes_tuple(self, tmp_path):
        score = self._build_score(tmp_path)
        with pytest.raises(ValidationError):
            score.outcomes = ()  # type: ignore[misc]

    def test_extra_fields_rejected(self, tmp_path):
        with pytest.raises(ValidationError):
            CaseScore(
                case_id="example_case",
                case_dir=tmp_path,
                outcomes=(),
                surprise="nope",  # type: ignore[call-arg]
            )

    def test_json_round_trip(self, tmp_path):
        original = self._build_score(tmp_path)
        text = original.model_dump_json()
        reconstituted = CaseScore.model_validate_json(text)
        assert reconstituted == original

    def test_dump_excludes_runtime_counts(self, tmp_path):
        score = self._build_score(tmp_path)
        parsed = json.loads(score.model_dump_json())
        assert set(parsed.keys()) == {
            "case_id",
            "case_dir",
            "outcomes",
        }

    def test_runtime_counts_accessible(self, tmp_path):
        score = self._build_score(tmp_path)
        assert score.total == 1
        assert score.passed == 0
        assert score.failed == 0
        assert score.inconclusive == 1
