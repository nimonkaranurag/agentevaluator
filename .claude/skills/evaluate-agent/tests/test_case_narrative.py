"""
Failure-mode tests for the case-narrative loader, schema, and citation validator.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evaluate_agent.case_narrative.citation_validator import (
    NarrativeCitationFailure,
    validate_narrative_citations,
    verify_narrative_against_score,
)
from evaluate_agent.case_narrative.loader import (
    load_case_narrative,
)
from evaluate_agent.case_narrative.schema import (
    CaseNarrative,
    NarrativeCitation,
    NarrativeObservation,
)
from evaluate_agent.common.errors.case_narrative import (
    CaseNarrativeNotFoundError,
    CaseNarrativeSyntaxError,
    CaseNarrativeValidationError,
    NarrativeCaseMismatchError,
    NarrativeCitationsUnresolvedError,
)
from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionPassed,
)
from evaluate_agent.scoring.scores import CaseScore
from pydantic import ValidationError


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _build_narrative(
    case_dir: Path, case_id: str = "c"
) -> CaseNarrative:
    artifact = case_dir / "trace" / "evidence.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("evidence", encoding="utf-8")
    return CaseNarrative(
        case_id=case_id,
        summary=(
            "agent answered the user's question without a "
            "tool call"
        ),
        observations=(
            NarrativeObservation(
                kind="behavior",
                claim="responded directly",
                citations=(
                    NarrativeCitation(
                        artifact_path=artifact
                    ),
                ),
            ),
        ),
    )


# ---------- schema ----------


def test_observation_requires_at_least_one_citation() -> (
    None
):
    # min_length=1 on citations is the citation contract:
    # an observation without citations is ungrounded prose.
    with pytest.raises(ValidationError):
        NarrativeObservation(
            kind="behavior",
            claim="x",
            citations=(),
        )


def test_narrative_requires_at_least_one_observation(
    tmp_path: Path,
) -> None:
    # Same min_length=1 contract at the narrative level —
    # a summary without supporting observations would render
    # as bare prose with no citation grounding.
    artifact = tmp_path / "evidence.txt"
    artifact.write_text("e", encoding="utf-8")
    with pytest.raises(ValidationError):
        CaseNarrative(
            case_id="c",
            summary="agent answered directly",
            observations=(),
        )


def test_observation_claim_max_length_enforced() -> None:
    artifact = Path("/dev/null")
    with pytest.raises(ValidationError):
        NarrativeObservation(
            kind="behavior",
            claim="x" * 600,
            citations=(
                NarrativeCitation(artifact_path=artifact),
            ),
        )


# ---------- loader ----------


def test_loader_raises_not_found(tmp_path: Path) -> None:
    with pytest.raises(CaseNarrativeNotFoundError):
        load_case_narrative(tmp_path / "missing.json")


def test_loader_raises_syntax_error_on_invalid_json(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "n.json", "{not json}")
    with pytest.raises(CaseNarrativeSyntaxError):
        load_case_narrative(path)


def test_loader_raises_syntax_error_for_top_level_array(
    tmp_path: Path,
) -> None:
    # JSON arrays bypass the field-level validator. Reject
    # before model_validate so the operator sees a precise
    # "expected an object" message.
    path = _write(tmp_path / "n.json", "[]")
    with pytest.raises(CaseNarrativeSyntaxError):
        load_case_narrative(path)


def test_loader_raises_validation_error_on_schema_violation(
    tmp_path: Path,
) -> None:
    payload = {
        "case_id": "c",
        "summary": "a summary",
        # observations missing — schema requires min_length=1
    }
    path = _write(tmp_path / "n.json", json.dumps(payload))
    with pytest.raises(CaseNarrativeValidationError):
        load_case_narrative(path)


# ---------- citation validator ----------


def test_validate_citations_accepts_path_under_case_dir(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    narrative = _build_narrative(case_dir)
    result = validate_narrative_citations(
        narrative, case_dir=case_dir
    )
    assert result.is_valid


def test_validate_citations_flags_missing_file(
    tmp_path: Path,
) -> None:
    # Path-shaped but doesn't resolve to a regular file —
    # narrative refers to evidence the operator promised but
    # didn't produce; surface this so the report doesn't ship
    # with broken citations.
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    bad = case_dir / "trace" / "missing.txt"
    narrative = CaseNarrative(
        case_id="c",
        summary="ungrounded summary",
        observations=(
            NarrativeObservation(
                kind="behavior",
                claim="x",
                citations=(
                    NarrativeCitation(artifact_path=bad),
                ),
            ),
        ),
    )
    result = validate_narrative_citations(
        narrative, case_dir=case_dir
    )
    assert not result.is_valid
    failure = result.failures[0]
    assert failure.failure_reason == "path_does_not_exist"


def test_validate_citations_flags_path_outside_case_dir(
    tmp_path: Path,
) -> None:
    # The narrative is bound to a case_dir; citations outside
    # that directory could be unrelated artifacts (or worse,
    # smuggled paths from other agents). Must reject.
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    narrative = CaseNarrative(
        case_id="c",
        summary="x",
        observations=(
            NarrativeObservation(
                kind="behavior",
                claim="x",
                citations=(
                    NarrativeCitation(
                        artifact_path=outside
                    ),
                ),
            ),
        ),
    )
    result = validate_narrative_citations(
        narrative, case_dir=case_dir
    )
    assert not result.is_valid
    failure = result.failures[0]
    assert (
        failure.failure_reason
        == "path_outside_case_directory"
    )


def test_failure_narrative_path_contains_indices(
    tmp_path: Path,
) -> None:
    # The narrative_path must be a JSON-style locator
    # (observations[i].citations[j].artifact_path) so the
    # operator can navigate from the failure straight to the
    # offending citation in the source file.
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    bad = case_dir / "missing.txt"
    narrative = CaseNarrative(
        case_id="c",
        summary="x",
        observations=(
            NarrativeObservation(
                kind="behavior",
                claim="x",
                citations=(
                    NarrativeCitation(artifact_path=bad),
                ),
            ),
        ),
    )
    failure = validate_narrative_citations(
        narrative, case_dir=case_dir
    ).failures[0]
    assert (
        failure.narrative_path
        == "observations[0].citations[0].artifact_path"
    )


def test_verify_narrative_against_score_rejects_case_id_mismatch(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    narrative = _build_narrative(case_dir, case_id="c")
    score = CaseScore(
        case_id="other",
        case_dir=case_dir,
        outcomes=(
            AssertionPassed(
                assertion_kind="must_call",
                target="lookup",
                evidence=AssertionEvidence(
                    artifact_path=case_dir
                    / "trace"
                    / "evidence.txt",
                    detail="ok",
                ),
            ),
        ),
    )
    with pytest.raises(NarrativeCaseMismatchError):
        verify_narrative_against_score(
            narrative, score=score
        )


def test_verify_narrative_against_score_propagates_citation_failures(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    bad = case_dir / "missing.txt"
    narrative = CaseNarrative(
        case_id="c",
        summary="x",
        observations=(
            NarrativeObservation(
                kind="behavior",
                claim="x",
                citations=(
                    NarrativeCitation(artifact_path=bad),
                ),
            ),
        ),
    )
    real = case_dir / "trace" / "evidence.txt"
    real.parent.mkdir()
    real.write_text("x", encoding="utf-8")
    score = CaseScore(
        case_id="c",
        case_dir=case_dir,
        outcomes=(
            AssertionPassed(
                assertion_kind="must_call",
                target="lookup",
                evidence=AssertionEvidence(
                    artifact_path=real, detail="ok"
                ),
            ),
        ),
    )
    with pytest.raises(NarrativeCitationsUnresolvedError):
        verify_narrative_against_score(
            narrative, score=score
        )
