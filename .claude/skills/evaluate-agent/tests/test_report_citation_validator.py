"""
Tests for validate_citations against CaseScore and AgentScore records.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.report import (
    CitationValidationFailure,
    CitationValidationResult,
    validate_citations,
)
from evaluate_agent.scoring import (
    AgentScore,
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    CaseScore,
    DOMSnapshotUnavailable,
    ObservabilitySourceMissing,
    score_agent,
)
from pydantic import ValidationError


def _make_evidence_file(
    case_dir: Path,
    name: str = "step-001-landing.html",
) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    target = case_dir / name
    target.write_text("<html></html>", encoding="utf-8")
    return target


def _passed(
    artifact_path: Path,
    *,
    kind="final_response_contains",
    target=None,
    detail=None,
) -> AssertionPassed:
    return AssertionPassed(
        assertion_kind=kind,
        target=target,
        evidence=AssertionEvidence(
            artifact_path=artifact_path,
            detail=detail,
        ),
    )


def _failed(
    artifact_path: Path,
    *,
    kind="final_response_contains",
    target=None,
    expected="needle",
    observed="haystack",
) -> AssertionFailed:
    return AssertionFailed(
        assertion_kind=kind,
        target=target,
        expected=expected,
        observed=observed,
        evidence=AssertionEvidence(
            artifact_path=artifact_path,
        ),
    )


def _inconclusive_obs(
    *,
    kind="must_call",
    target="search",
    needed="tool_call_log",
) -> AssertionInconclusive:
    return AssertionInconclusive(
        assertion_kind=kind,
        target=target,
        reason=ObservabilitySourceMissing(
            needed_evidence=needed,
        ),
    )


def _inconclusive_dom(
    expected_dir: Path,
    *,
    kind="final_response_contains",
) -> AssertionInconclusive:
    return AssertionInconclusive(
        assertion_kind=kind,
        reason=DOMSnapshotUnavailable(
            expected_artifact_dir=expected_dir,
        ),
    )


def _build_case_score(
    case_dir: Path,
    outcomes,
    case_id: str = "happy_case",
) -> CaseScore:
    return CaseScore(
        case_id=case_id,
        case_dir=case_dir,
        outcomes=tuple(outcomes),
    )


def _build_agent_score(
    *,
    runs_root: Path,
    manifest_path: Path,
    case_scores,
    agent_name: str = "test_agent",
    run_id: str = "20260425T173000Z",
) -> AgentScore:
    return score_agent(
        case_scores=tuple(case_scores),
        agent_name=agent_name,
        run_id=run_id,
        runs_root=runs_root,
        manifest_path=manifest_path,
    )


class TestCaseScoreAllResolve:
    def test_passed_evidence_resolves(self, tmp_path):
        case_dir = tmp_path / "case-a"
        artifact = _make_evidence_file(case_dir)
        score = _build_case_score(
            case_dir,
            [_passed(artifact)],
        )
        result = validate_citations(score)
        assert result.is_valid
        assert result.failures == ()

    def test_failed_evidence_resolves(self, tmp_path):
        case_dir = tmp_path / "case-b"
        artifact = _make_evidence_file(
            case_dir, "step-002-after_submit.html"
        )
        score = _build_case_score(
            case_dir,
            [_failed(artifact)],
        )
        result = validate_citations(score)
        assert result.is_valid

    def test_inconclusive_outcomes_have_no_path_to_resolve(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-c"
        case_dir.mkdir()
        score = _build_case_score(
            case_dir,
            [
                _inconclusive_obs(),
                _inconclusive_dom(case_dir / "trace"),
            ],
        )
        result = validate_citations(score)
        assert result.is_valid

    def test_empty_outcomes_only_validates_case_dir(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-d"
        case_dir.mkdir()
        score = _build_case_score(case_dir, [])
        result = validate_citations(score)
        assert result.is_valid


class TestCaseScoreFailures:
    def test_missing_case_dir(self, tmp_path):
        case_dir = tmp_path / "never_created"
        score = _build_case_score(
            case_dir, [], case_id="missing_dir"
        )
        result = validate_citations(score)
        assert not result.is_valid
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure.score_path == "case_dir"
        assert failure.artifact_path == case_dir
        assert failure.expected_kind == "directory"

    def test_case_dir_is_a_file_not_a_directory(
        self, tmp_path
    ):
        intruder = tmp_path / "actually_a_file"
        intruder.write_text("hi", encoding="utf-8")
        score = _build_case_score(intruder, [])
        result = validate_citations(score)
        assert len(result.failures) == 1
        assert (
            result.failures[0].expected_kind == "directory"
        )

    def test_passed_evidence_path_missing(self, tmp_path):
        case_dir = tmp_path / "case-e"
        case_dir.mkdir()
        ghost = case_dir / "ghost.html"
        score = _build_case_score(
            case_dir, [_passed(ghost)]
        )
        result = validate_citations(score)
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert (
            failure.score_path
            == "outcomes[0].evidence.artifact_path"
        )
        assert failure.artifact_path == ghost
        assert failure.expected_kind == "file"

    def test_failed_evidence_path_missing(self, tmp_path):
        case_dir = tmp_path / "case-f"
        case_dir.mkdir()
        ghost = case_dir / "ghost.html"
        score = _build_case_score(
            case_dir, [_failed(ghost)]
        )
        result = validate_citations(score)
        assert len(result.failures) == 1
        assert result.failures[0].expected_kind == "file"

    def test_evidence_path_is_a_directory_not_a_file(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-g"
        wrong_kind = case_dir / "subdir"
        wrong_kind.mkdir(parents=True)
        score = _build_case_score(
            case_dir, [_passed(wrong_kind)]
        )
        result = validate_citations(score)
        assert len(result.failures) == 1
        assert result.failures[0].expected_kind == "file"

    def test_multiple_failures_in_one_case(self, tmp_path):
        case_dir = tmp_path / "case-h"
        case_dir.mkdir()
        ghost1 = case_dir / "ghost1.html"
        ghost2 = case_dir / "ghost2.html"
        score = _build_case_score(
            case_dir,
            [
                _passed(ghost1),
                _failed(ghost2),
            ],
        )
        result = validate_citations(score)
        assert len(result.failures) == 2
        score_paths = {
            f.score_path for f in result.failures
        }
        assert score_paths == {
            "outcomes[0].evidence.artifact_path",
            "outcomes[1].evidence.artifact_path",
        }

    def test_inconclusive_does_not_contribute_failures(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-i"
        case_dir.mkdir()
        artifact = _make_evidence_file(case_dir)
        score = _build_case_score(
            case_dir,
            [
                _passed(artifact),
                _inconclusive_obs(),
                _inconclusive_dom(case_dir / "missing"),
            ],
        )
        result = validate_citations(score)
        assert result.is_valid

    def test_failures_preserve_outcome_order(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-j"
        case_dir.mkdir()
        artifact = _make_evidence_file(case_dir)
        ghost = case_dir / "ghost.html"
        score = _build_case_score(
            case_dir,
            [
                _passed(artifact),
                _failed(ghost),
                _passed(artifact),
            ],
        )
        result = validate_citations(score)
        assert len(result.failures) == 1
        assert (
            result.failures[0].score_path
            == "outcomes[1].evidence.artifact_path"
        )


class TestAgentScoreAllResolve:
    def test_full_agent_score_resolves(self, tmp_path):
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        manifest = tmp_path / "agent.yaml"
        manifest.write_text("stub", encoding="utf-8")
        case_dir_a = runs_root / "case-a"
        case_dir_b = runs_root / "case-b"
        artifact_a = _make_evidence_file(case_dir_a)
        artifact_b = _make_evidence_file(case_dir_b)
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir_a,
                    [_passed(artifact_a)],
                    case_id="case_a",
                ),
                _build_case_score(
                    case_dir_b,
                    [_failed(artifact_b)],
                    case_id="case_b",
                ),
            ],
        )
        result = validate_citations(agent_score)
        assert result.is_valid


class TestAgentScoreFailures:
    def test_runs_root_missing(self, tmp_path):
        runs_root = tmp_path / "ghost_runs"
        manifest = tmp_path / "agent.yaml"
        manifest.write_text("stub", encoding="utf-8")
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        artifact = _make_evidence_file(case_dir)
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [_passed(artifact)]
                )
            ],
        )
        result = validate_citations(agent_score)
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure.score_path == "runs_root"
        assert failure.expected_kind == "directory"

    def test_manifest_path_missing(self, tmp_path):
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        ghost_manifest = tmp_path / "ghost.yaml"
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        artifact = _make_evidence_file(case_dir)
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=ghost_manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [_passed(artifact)]
                )
            ],
        )
        result = validate_citations(agent_score)
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure.score_path == "manifest_path"
        assert failure.expected_kind == "file"

    def test_manifest_path_is_directory_not_file(
        self, tmp_path
    ):
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        manifest_dir = tmp_path / "agent.yaml"
        manifest_dir.mkdir()
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        artifact = _make_evidence_file(case_dir)
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest_dir,
            case_scores=[
                _build_case_score(
                    case_dir, [_passed(artifact)]
                )
            ],
        )
        result = validate_citations(agent_score)
        assert (
            result.failures[0].score_path == "manifest_path"
        )
        assert result.failures[0].expected_kind == "file"

    def test_case_dir_missing_inside_agent_score(
        self, tmp_path
    ):
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        manifest = tmp_path / "agent.yaml"
        manifest.write_text("stub", encoding="utf-8")
        case_dir = tmp_path / "ghost_case"
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(case_dir, []),
            ],
        )
        result = validate_citations(agent_score)
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert (
            failure.score_path == "case_scores[0].case_dir"
        )
        assert failure.expected_kind == "directory"

    def test_evidence_path_inside_agent_score(
        self, tmp_path
    ):
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        manifest = tmp_path / "agent.yaml"
        manifest.write_text("stub", encoding="utf-8")
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        ghost = case_dir / "ghost.html"
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [_passed(ghost)]
                ),
            ],
        )
        result = validate_citations(agent_score)
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert (
            failure.score_path
            == "case_scores[0].outcomes[0]"
            ".evidence.artifact_path"
        )

    def test_failures_across_multiple_cases_keep_index(
        self, tmp_path
    ):
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        manifest = tmp_path / "agent.yaml"
        manifest.write_text("stub", encoding="utf-8")
        case_dir_a = tmp_path / "case-a"
        case_dir_b = tmp_path / "case-b"
        case_dir_a.mkdir()
        case_dir_b.mkdir()
        artifact_a = _make_evidence_file(case_dir_a)
        ghost_b = case_dir_b / "ghost.html"
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir_a,
                    [_passed(artifact_a)],
                    case_id="case_a",
                ),
                _build_case_score(
                    case_dir_b,
                    [_failed(ghost_b)],
                    case_id="case_b",
                ),
            ],
        )
        result = validate_citations(agent_score)
        assert len(result.failures) == 1
        assert (
            result.failures[0].score_path
            == "case_scores[1].outcomes[0]"
            ".evidence.artifact_path"
        )

    def test_aggregates_top_level_and_per_case_failures(
        self, tmp_path
    ):
        runs_root = tmp_path / "ghost_runs"
        ghost_manifest = tmp_path / "ghost.yaml"
        case_dir = tmp_path / "ghost_case"
        agent_score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=ghost_manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="ghost"
                )
            ],
        )
        result = validate_citations(agent_score)
        score_paths = sorted(
            f.score_path for f in result.failures
        )
        assert score_paths == [
            "case_scores[0].case_dir",
            "manifest_path",
            "runs_root",
        ]


class TestResultAndFailureSchema:
    def test_result_is_frozen(self, tmp_path):
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        result = validate_citations(
            _build_case_score(case_dir, [])
        )
        with pytest.raises(ValidationError):
            result.failures = ()  # type: ignore[misc]

    def test_failure_is_frozen(self, tmp_path):
        failure = CitationValidationFailure(
            score_path="x",
            artifact_path=tmp_path / "ghost",
            expected_kind="file",
        )
        with pytest.raises(ValidationError):
            failure.score_path = "y"  # type: ignore[misc]

    def test_failure_extra_fields_rejected(self, tmp_path):
        with pytest.raises(ValidationError):
            CitationValidationFailure(
                score_path="x",
                artifact_path=tmp_path / "ghost",
                expected_kind="file",
                surprise="nope",  # type: ignore[call-arg]
            )

    def test_failure_score_path_min_length(self, tmp_path):
        with pytest.raises(ValidationError):
            CitationValidationFailure(
                score_path="",
                artifact_path=tmp_path / "ghost",
                expected_kind="file",
            )

    def test_failure_expected_kind_constrained(
        self, tmp_path
    ):
        with pytest.raises(ValidationError):
            CitationValidationFailure(
                score_path="x",
                artifact_path=tmp_path / "ghost",
                expected_kind="symlink",  # type: ignore[arg-type]
            )

    def test_result_is_valid_property(self, tmp_path):
        empty = CitationValidationResult(failures=())
        assert empty.is_valid
        non_empty = CitationValidationResult(
            failures=(
                CitationValidationFailure(
                    score_path="x",
                    artifact_path=tmp_path / "ghost",
                    expected_kind="file",
                ),
            ),
        )
        assert not non_empty.is_valid


class TestUnsupportedInputType:
    def test_raises_typeerror_on_arbitrary_input(self):
        with pytest.raises(TypeError):
            validate_citations(
                "not a score"  # type: ignore[arg-type]
            )

    def test_raises_typeerror_on_dict_input(self):
        with pytest.raises(TypeError):
            validate_citations(
                {"case_id": "x"}  # type: ignore[arg-type]
            )
