"""
Tests for render_case_score_markdown and compose_case_section.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.report import (
    UnresolvedCitationError,
    compose_case_section,
    render_case_score_markdown,
)
from evaluate_agent.scoring import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionPassed,
    CaseScore,
    DOMSnapshotUnavailable,
    ObservabilitySourceMissing,
)


def _seed_evidence(
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
    detail=None,
) -> AssertionFailed:
    return AssertionFailed(
        assertion_kind=kind,
        target=target,
        expected=expected,
        observed=observed,
        evidence=AssertionEvidence(
            artifact_path=artifact_path,
            detail=detail,
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


def _build(
    case_dir: Path,
    outcomes,
    *,
    case_id: str = "happy_case",
) -> CaseScore:
    return CaseScore(
        case_id=case_id,
        case_dir=case_dir,
        outcomes=tuple(outcomes),
    )


class TestStandaloneRenderHeader:
    def test_h1_is_used_for_top_level_heading(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        markdown = render_case_score_markdown(
            _build(case_dir, [], case_id="login_flow")
        )
        assert markdown.startswith("# Case `login_flow` —")

    def test_summary_line_carries_per_status_counts(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-b"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        score = _build(
            case_dir,
            [
                _passed(artifact),
                _failed(artifact),
                _inconclusive_obs(),
            ],
        )
        markdown = render_case_score_markdown(score)
        first_line = markdown.splitlines()[0]
        assert (
            "1 passed, 1 failed, 1 inconclusive "
            "(of 3 total)" in first_line
        )

    def test_directory_line_renders_absolute_path(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-c"
        case_dir.mkdir()
        markdown = render_case_score_markdown(
            _build(case_dir, [])
        )
        assert f"**Directory:** `{case_dir}`" in markdown


class TestEmptyOutcomes:
    def test_renders_no_assertions_message(self, tmp_path):
        case_dir = tmp_path / "case-d"
        case_dir.mkdir()
        markdown = render_case_score_markdown(
            _build(case_dir, [])
        )
        assert (
            "No assertions declared for this case."
            in markdown
        )

    def test_does_not_render_outcomes_section(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-e"
        case_dir.mkdir()
        markdown = render_case_score_markdown(
            _build(case_dir, [])
        )
        assert "**Assertion outcomes:**" not in markdown


class TestPassedRendering:
    def test_evidence_path_cited_in_backticks(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-f"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(case_dir, [_passed(artifact)])
        )
        assert f"Evidence: `{artifact}`" in markdown

    def test_status_label_is_uppercase_passed(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-g"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(case_dir, [_passed(artifact)])
        )
        assert "**PASSED**" in markdown

    def test_target_renders_with_em_dash_when_present(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-h"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(
                case_dir,
                [
                    _passed(
                        artifact,
                        kind="must_call",
                        target="search_flights",
                    )
                ],
            )
        )
        assert (
            "`must_call` — target `search_flights`"
            in markdown
        )

    def test_target_omitted_for_whole_case_assertion(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-i"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(case_dir, [_passed(artifact)])
        )
        assert "— target `" not in markdown

    def test_detail_line_appears_when_provided(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-j"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(
                case_dir,
                [
                    _passed(
                        artifact,
                        detail="matched at offset 42",
                    )
                ],
            )
        )
        assert "Detail: matched at offset 42" in markdown

    def test_detail_line_omitted_when_none(self, tmp_path):
        case_dir = tmp_path / "case-k"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(case_dir, [_passed(artifact)])
        )
        assert "Detail:" not in markdown


class TestFailedRendering:
    def test_status_label_is_uppercase_failed(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-l"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(case_dir, [_failed(artifact)])
        )
        assert "**FAILED**" in markdown

    def test_expected_and_observed_rendered_in_backticks(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-m"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        markdown = render_case_score_markdown(
            _build(
                case_dir,
                [
                    _failed(
                        artifact,
                        expected="confirmed",
                        observed="delayed",
                    )
                ],
            )
        )
        assert "Expected: `confirmed`" in markdown
        assert "Observed: `delayed`" in markdown

    def test_observed_none_renders_explicit_marker(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-n"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        outcome = AssertionFailed(
            assertion_kind="final_response_contains",
            expected="needle",
            observed=None,
            evidence=AssertionEvidence(
                artifact_path=artifact,
            ),
        )
        markdown = render_case_score_markdown(
            _build(case_dir, [outcome])
        )
        assert "Observed: (none)" in markdown


class TestInconclusiveRendering:
    def test_status_label_is_uppercase_inconclusive(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-o"
        case_dir.mkdir()
        markdown = render_case_score_markdown(
            _build(
                case_dir,
                [_inconclusive_obs()],
            )
        )
        assert "**INCONCLUSIVE**" in markdown

    def test_observability_missing_renders_needed_evidence(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-p"
        case_dir.mkdir()
        markdown = render_case_score_markdown(
            _build(
                case_dir,
                [
                    _inconclusive_obs(
                        needed="routing_decision_log",
                    )
                ],
            )
        )
        assert (
            "Reason: `observability_source_missing`"
            in markdown
        )
        assert (
            "Needed evidence: "
            "`routing_decision_log`" in markdown
        )

    def test_dom_unavailable_renders_expected_dir(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-q"
        case_dir.mkdir()
        expected_dir = case_dir / "trace" / "dom"
        markdown = render_case_score_markdown(
            _build(
                case_dir,
                [_inconclusive_dom(expected_dir)],
            )
        )
        assert (
            "Reason: `dom_snapshot_unavailable`" in markdown
        )
        assert (
            f"Expected artifact dir: "
            f"`{expected_dir}`" in markdown
        )

    def test_recovery_text_relayed_verbatim(self, tmp_path):
        case_dir = tmp_path / "case-r"
        case_dir.mkdir()
        outcome = _inconclusive_obs()
        markdown = render_case_score_markdown(
            _build(case_dir, [outcome])
        )
        assert (
            f"Recovery: {outcome.reason.recovery}"
            in markdown
        )


class TestOutcomeOrderingPreserved:
    def test_outcomes_render_in_declared_order(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-s"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        score = _build(
            case_dir,
            [
                _passed(
                    artifact,
                    kind="final_response_contains",
                ),
                _inconclusive_obs(
                    kind="must_call",
                    target="alpha",
                ),
                _inconclusive_obs(
                    kind="must_call",
                    target="beta",
                ),
                _failed(
                    artifact,
                    kind="must_route_to",
                    target="tier2",
                ),
            ],
        )
        markdown = render_case_score_markdown(score)
        offsets = [
            markdown.find("`final_response_contains`"),
            markdown.find("target `alpha`"),
            markdown.find("target `beta`"),
            markdown.find("target `tier2`"),
        ]
        assert all(o > 0 for o in offsets)
        assert offsets == sorted(offsets)


class TestCitationValidationIntegration:
    def test_missing_evidence_path_raises_error(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-t"
        case_dir.mkdir()
        ghost = case_dir / "ghost.html"
        score = _build(case_dir, [_passed(ghost)])
        with pytest.raises(UnresolvedCitationError) as info:
            render_case_score_markdown(score)
        assert info.value.failures
        assert info.value.failures[0].artifact_path == ghost

    def test_missing_case_dir_raises_error(self, tmp_path):
        case_dir = tmp_path / "ghost"
        score = _build(case_dir, [])
        with pytest.raises(UnresolvedCitationError):
            render_case_score_markdown(score)

    def test_error_message_lists_recovery(self, tmp_path):
        case_dir = tmp_path / "case-u"
        case_dir.mkdir()
        ghost = case_dir / "ghost.html"
        score = _build(case_dir, [_passed(ghost)])
        with pytest.raises(UnresolvedCitationError) as info:
            render_case_score_markdown(score)
        assert "To proceed:" in str(info.value)
        assert "render_report.py" in str(info.value)


class TestComposeCaseSectionHeadingLevels:
    def test_default_h1_when_called_directly(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-v"
        case_dir.mkdir()
        section = compose_case_section(
            _build(case_dir, []), heading_level=1
        )
        assert section.startswith("# Case ")

    def test_h3_section_for_embedding(self, tmp_path):
        case_dir = tmp_path / "case-w"
        case_dir.mkdir()
        section = compose_case_section(
            _build(case_dir, []), heading_level=3
        )
        assert section.startswith("### Case ")

    def test_compose_does_not_validate_citations(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-x"
        case_dir.mkdir()
        ghost = case_dir / "ghost.html"
        section = compose_case_section(
            _build(case_dir, [_passed(ghost)]),
            heading_level=2,
        )
        assert "**PASSED**" in section
        assert f"`{ghost}`" in section

    @pytest.mark.parametrize("level", [0, -1, 7, 100])
    def test_invalid_heading_level_rejected(
        self, tmp_path, level
    ):
        case_dir = tmp_path / "case-y"
        case_dir.mkdir()
        with pytest.raises(ValueError):
            compose_case_section(
                _build(case_dir, []),
                heading_level=level,
            )


class TestTrailingNewline:
    def test_output_ends_with_single_newline(
        self, tmp_path
    ):
        case_dir = tmp_path / "case-z"
        case_dir.mkdir()
        markdown = render_case_score_markdown(
            _build(case_dir, [])
        )
        assert markdown.endswith("\n")
        assert not markdown.endswith("\n\n")
