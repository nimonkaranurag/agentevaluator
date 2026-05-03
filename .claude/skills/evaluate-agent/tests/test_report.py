"""
Failure-mode tests for report citation validation, the case-score and agent-score renderers, and UnresolvedCitationError formatting.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.case_narrative.schema import (
    CaseNarrative,
    NarrativeCitation,
    NarrativeObservation,
)
from evaluate_agent.common.errors.report import (
    UnresolvedCitationError,
)
from evaluate_agent.report.common.citation_validator import (
    CitationValidationFailure,
    validate_citations,
)
from evaluate_agent.report.renderers.agent_score import (
    render_agent_score_markdown,
)
from evaluate_agent.report.renderers.case_score import (
    render_case_score_markdown,
)
from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    DOMSnapshotUnavailable,
    GenerationCoverageIncomplete,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)
from evaluate_agent.scoring.scores import (
    CaseScore,
    score_agent,
)

_RUN_ID = "20260425T173000Z"


def _real_artifact(case_dir: Path) -> Path:
    path = case_dir / "trace" / "evidence.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("e", encoding="utf-8")
    return path


def _passed_outcome(path: Path) -> AssertionPassed:
    return AssertionPassed(
        assertion_kind="must_call",
        target="lookup",
        evidence=AssertionEvidence(
            artifact_path=path, detail="ok"
        ),
    )


def _failed_outcome(path: Path) -> AssertionFailed:
    return AssertionFailed(
        assertion_kind="must_call",
        target="forbidden",
        expected="forbidden",
        observed="ok",
        evidence=AssertionEvidence(
            artifact_path=path, detail="bad"
        ),
    )


def _inconclusive_no_log(
    case_dir: Path,
) -> AssertionInconclusive:
    return AssertionInconclusive(
        assertion_kind="must_call",
        target="lookup",
        reason=ObservabilitySourceMissing(
            needed_evidence="tool_call_log",
            expected_artifact_path=case_dir
            / "trace"
            / "observability"
            / "tool_calls.jsonl",
        ),
    )


# ---------- citation validator ----------


def test_validate_citations_flags_missing_evidence(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    score = CaseScore(
        case_id="c",
        case_dir=case_dir,
        outcomes=(
            _passed_outcome(case_dir / "missing.txt"),
        ),
    )
    result = validate_citations(score)
    assert not result.is_valid
    assert result.failures[0].expected_kind == "file"
    assert (
        "outcomes[0].evidence.artifact_path"
        in result.failures[0].score_path
    )


def test_validate_citations_flags_missing_case_dir(
    tmp_path: Path,
) -> None:
    # case_dir itself is a citation. A missing case_dir would
    # leave every outcome's artifact_path orphaned, so the
    # validator must surface that as the first failure.
    score = CaseScore(
        case_id="c",
        case_dir=tmp_path / "absent",
        outcomes=(),
    )
    result = validate_citations(score)
    assert not result.is_valid
    assert result.failures[0].expected_kind == "directory"


def test_validate_citations_does_not_check_inconclusive_outcomes(
    tmp_path: Path,
) -> None:
    # Inconclusive outcomes carry no evidence path — they are
    # by definition the case where the citation could not be
    # produced. Validating them as files would always fail.
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    score = CaseScore(
        case_id="c",
        case_dir=case_dir,
        outcomes=(_inconclusive_no_log(case_dir),),
    )
    result = validate_citations(score)
    assert result.is_valid


def test_validate_citations_rejects_unsupported_score_type() -> (
    None
):
    with pytest.raises(TypeError):
        validate_citations("not-a-score")  # type: ignore[arg-type]


# ---------- UnresolvedCitationError ----------


def test_unresolved_citation_error_requires_at_least_one_failure() -> (
    None
):
    # Constructing with empty failures means the validator
    # said "valid" but the renderer raised anyway — that's a
    # caller bug worth catching at construction time, not
    # silently propagating an empty error.
    with pytest.raises(ValueError):
        UnresolvedCitationError(failures=())


def test_unresolved_citation_error_message_lists_every_failure(
    tmp_path: Path,
) -> None:
    failures = (
        CitationValidationFailure(
            score_path="case_scores[0].case_dir",
            artifact_path=tmp_path / "missing-1",
            expected_kind="directory",
        ),
        CitationValidationFailure(
            score_path=(
                "case_scores[0].outcomes[2]"
                ".evidence.artifact_path"
            ),
            artifact_path=tmp_path / "missing-2.txt",
            expected_kind="file",
        ),
    )
    err = UnresolvedCitationError(failures)
    text = str(err)
    assert "2 citation(s)" in text
    assert "case_scores[0].case_dir" in text
    assert "missing-1" in text
    assert "missing-2.txt" in text


# ---------- case-score renderer ----------


def test_render_case_score_includes_summary_and_outcomes(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    artifact = _real_artifact(case_dir)
    score = CaseScore(
        case_id="c",
        case_dir=case_dir,
        outcomes=(
            _passed_outcome(artifact),
            _failed_outcome(artifact),
            _inconclusive_no_log(case_dir),
        ),
    )
    text = render_case_score_markdown(score)
    assert "# Case `c`" in text
    assert "1 passed" in text
    assert "PASSED" in text
    assert "FAILED" in text
    assert "INCONCLUSIVE" in text


def test_render_case_score_raises_on_unresolved_citations(
    tmp_path: Path,
) -> None:
    # The renderer is the trust boundary — any score whose
    # citations don't resolve must abort rather than ship a
    # report referencing missing files.
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    score = CaseScore(
        case_id="c",
        case_dir=case_dir,
        outcomes=(
            _passed_outcome(case_dir / "missing.txt"),
        ),
    )
    with pytest.raises(UnresolvedCitationError):
        render_case_score_markdown(score)


def test_render_case_score_supports_no_assertion_case(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    score = CaseScore(
        case_id="c", case_dir=case_dir, outcomes=()
    )
    text = render_case_score_markdown(score)
    assert "No assertions declared for this case." in text


def test_render_case_score_renders_inconclusive_reasons(
    tmp_path: Path,
) -> None:
    # Each InconclusiveReason variant has its own renderer
    # branch. Exercising them confirms the renderer never
    # silently drops a reason kind.
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    artifact = _real_artifact(case_dir)
    log_path = (
        case_dir
        / "trace"
        / "observability"
        / "generations.jsonl"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    outcomes = (
        AssertionInconclusive(
            assertion_kind="final_response_contains",
            reason=DOMSnapshotUnavailable(
                expected_artifact_dir=case_dir
                / "trace"
                / "dom",
            ),
        ),
        AssertionInconclusive(
            assertion_kind="max_total_tokens",
            reason=GenerationCoverageIncomplete(
                field="total_tokens",
                populated=1,
                total=2,
                log_path=log_path,
            ),
        ),
        AssertionInconclusive(
            assertion_kind="must_call",
            reason=ObservabilityLogMalformed(
                log_path=log_path,
                line_number=3,
                parse_error="invalid JSON (xyz)",
            ),
        ),
    )
    score = CaseScore(
        case_id="c", case_dir=case_dir, outcomes=outcomes
    )
    text = render_case_score_markdown(score)
    assert "dom_snapshot_unavailable" in text
    assert "generation_coverage_incomplete" in text
    assert "observability_log_malformed" in text


def test_render_case_score_embeds_narrative_when_provided(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    artifact = _real_artifact(case_dir)
    score = CaseScore(
        case_id="c",
        case_dir=case_dir,
        outcomes=(_passed_outcome(artifact),),
    )
    narrative = CaseNarrative(
        case_id="c",
        summary="agent answered directly",
        observations=(
            NarrativeObservation(
                kind="behavior",
                claim="responded without tool",
                citations=(
                    NarrativeCitation(
                        artifact_path=artifact
                    ),
                ),
            ),
        ),
    )
    text = render_case_score_markdown(
        score, narrative=narrative
    )
    assert "agent answered directly" in text


# ---------- agent-score renderer ----------


def test_render_agent_score_assembles_full_report(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case_a"
    case_dir.mkdir()
    artifact = _real_artifact(case_dir)
    manifest_path = tmp_path / "agent.yaml"
    manifest_path.write_text("apiVersion: v1\n")
    score = score_agent(
        case_scores=(
            CaseScore(
                case_id="case_a",
                case_dir=case_dir,
                outcomes=(_passed_outcome(artifact),),
            ),
        ),
        agent_name="demo",
        run_id=_RUN_ID,
        runs_root=tmp_path,
        manifest_path=manifest_path,
    )
    text = render_agent_score_markdown(score)
    assert "# Agent evaluation report" in text
    assert "demo" in text
    assert _RUN_ID in text
    assert "Case `case_a`" in text


def test_render_agent_score_raises_on_unknown_narrative_case_id(
    tmp_path: Path,
) -> None:
    # Narratives indexed by case_id must reference cases that
    # exist in the score; an unknown id is a mistake the
    # renderer surfaces rather than silently dropping the
    # narrative.
    case_dir = tmp_path / "case_a"
    case_dir.mkdir()
    artifact = _real_artifact(case_dir)
    manifest_path = tmp_path / "agent.yaml"
    manifest_path.write_text("apiVersion: v1\n")
    score = score_agent(
        case_scores=(
            CaseScore(
                case_id="case_a",
                case_dir=case_dir,
                outcomes=(_passed_outcome(artifact),),
            ),
        ),
        agent_name="demo",
        run_id=_RUN_ID,
        runs_root=tmp_path,
        manifest_path=manifest_path,
    )
    stray = CaseNarrative(
        case_id="case_b",
        summary="x",
        observations=(
            NarrativeObservation(
                kind="behavior",
                claim="x",
                citations=(
                    NarrativeCitation(
                        artifact_path=artifact
                    ),
                ),
            ),
        ),
    )
    with pytest.raises(Exception) as info:
        render_agent_score_markdown(
            score, narratives={"case_b": stray}
        )
    assert "case_b" in str(info.value)
