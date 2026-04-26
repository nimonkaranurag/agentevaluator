"""
Tests for render_agent_score_markdown.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.report import (
    UnresolvedCitationError,
    render_agent_score_markdown,
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


def _seed_evidence(
    case_dir: Path,
    name: str = "step-001-landing.html",
) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    target = case_dir / name
    target.write_text("<html></html>", encoding="utf-8")
    return target


def _passed(
    artifact: Path,
    *,
    kind="final_response_contains",
    target=None,
    detail=None,
) -> AssertionPassed:
    return AssertionPassed(
        assertion_kind=kind,
        target=target,
        evidence=AssertionEvidence(
            artifact_path=artifact,
            detail=detail,
        ),
    )


def _failed(
    artifact: Path,
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
            artifact_path=artifact,
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
            expected_artifact_path=Path(
                "/tmp/agent/case/trace/observability/"
                f"{needed}.jsonl"
            ),
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
    *,
    case_id: str,
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


def _scaffold(
    tmp_path: Path,
) -> tuple[Path, Path]:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    manifest = tmp_path / "agent.yaml"
    manifest.write_text("stub", encoding="utf-8")
    return runs_root, manifest


class TestHeaderSection:
    def test_h1_uses_agent_name_in_backticks(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            agent_name="flight_booking_agent",
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="case_a"
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert markdown.startswith(
            "# Agent evaluation report — "
            "`flight_booking_agent`"
        )

    def test_run_id_line_present(self, tmp_path):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            run_id="20260425T173000Z",
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="case_a"
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "**Run id:** `20260425T173000Z`" in markdown

    def test_manifest_path_and_runs_root_lines_present(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="case_a"
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert f"**Manifest:** `{manifest}`" in markdown
        assert f"**Runs root:** `{runs_root}`" in markdown


class TestSummarySection:
    def test_summary_table_renders_totals(self, tmp_path):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir,
                    [
                        _passed(artifact),
                        _failed(artifact),
                        _inconclusive_obs(),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "## Summary" in markdown
        assert "| Assertions | 3 | 1 | 1 | 1 |" in markdown


class TestByAssertionKindSection:
    def test_section_present_when_outcomes_exist(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir,
                    [
                        _passed(artifact),
                        _inconclusive_obs(),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "## By assertion kind" in markdown

    def test_rows_listed_in_schema_order(self, tmp_path):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
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
                            kind="must_not_call",
                            target="beta",
                        ),
                        _inconclusive_obs(
                            kind="must_route_to",
                            target="gamma",
                            needed=("routing_decision_log"),
                        ),
                        _inconclusive_obs(
                            kind="max_steps",
                            target=None,
                            needed="step_count",
                        ),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        offsets = [
            markdown.find("| `final_response_contains` |"),
            markdown.find("| `must_call` |"),
            markdown.find("| `must_not_call` |"),
            markdown.find("| `must_route_to` |"),
            markdown.find("| `max_steps` |"),
        ]
        assert all(o > 0 for o in offsets)
        assert offsets == sorted(offsets)

    def test_section_omitted_when_no_outcomes(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="case_a"
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "## By assertion kind" not in markdown


class TestByTargetSection:
    def test_section_present_for_targeted_kinds(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir,
                    [
                        _inconclusive_obs(
                            kind="must_call",
                            target="alpha",
                        ),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "## By target" in markdown
        assert "| `must_call` | `alpha` |" in markdown

    def test_section_omitted_when_no_target_outcomes(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir,
                    [
                        _passed(
                            artifact,
                            kind=(
                                "final_response_contains"
                            ),
                        ),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "## By target" not in markdown

    def test_targets_sort_lex_within_kind_schema_order(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir,
                    [
                        _inconclusive_obs(
                            kind="must_call",
                            target="zebra",
                        ),
                        _inconclusive_obs(
                            kind="must_call",
                            target="alpha",
                        ),
                        _inconclusive_obs(
                            kind="must_route_to",
                            target="beta",
                            needed=("routing_decision_log"),
                        ),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        offsets = [
            markdown.find("| `must_call` | `alpha` |"),
            markdown.find("| `must_call` | `zebra` |"),
            markdown.find("| `must_route_to` | `beta` |"),
        ]
        assert all(o > 0 for o in offsets)
        assert offsets == sorted(offsets)


class TestByCaseSection:
    def test_section_renders_case_rollup_row(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir_a = runs_root / "case-a"
        case_dir_b = runs_root / "case-b"
        case_dir_a.mkdir()
        case_dir_b.mkdir()
        artifact_a = _seed_evidence(case_dir_a)
        score = _build_agent_score(
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
                    [],
                    case_id="case_b",
                ),
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "## By case" in markdown
        assert "| 2 | 1 | 0 | 0 | 1 |" in markdown


class TestPerCaseDetailSection:
    def test_per_case_detail_section_renders_h3_per_case(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir_a = runs_root / "case-a"
        case_dir_b = runs_root / "case-b"
        case_dir_a.mkdir()
        case_dir_b.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir_a, [], case_id="case_a"
                ),
                _build_case_score(
                    case_dir_b, [], case_id="case_b"
                ),
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "## Per-case detail" in markdown
        assert "### Case `case_a`" in markdown
        assert "### Case `case_b`" in markdown

    def test_cases_appear_in_declaration_order(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir_a = runs_root / "case-a"
        case_dir_b = runs_root / "case-b"
        case_dir_a.mkdir()
        case_dir_b.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir_b,
                    [],
                    case_id="zebra_case",
                ),
                _build_case_score(
                    case_dir_a,
                    [],
                    case_id="apple_case",
                ),
            ],
        )
        markdown = render_agent_score_markdown(score)
        z_offset = markdown.find("### Case `zebra_case`")
        a_offset = markdown.find("### Case `apple_case`")
        assert z_offset > 0
        assert a_offset > z_offset

    def test_per_case_outcomes_render_inside_section(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        artifact = _seed_evidence(case_dir)
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir,
                    [
                        _passed(
                            artifact,
                            detail="matched offset 1",
                        ),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert "**PASSED**" in markdown
        assert "Detail: matched offset 1" in markdown
        assert f"Evidence: `{artifact}`" in markdown


class TestCitationValidationIntegration:
    def test_missing_runs_root_raises_error(self, tmp_path):
        runs_root = tmp_path / "ghost"
        manifest = tmp_path / "agent.yaml"
        manifest.write_text("stub", encoding="utf-8")
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="case_a"
                )
            ],
        )
        with pytest.raises(UnresolvedCitationError):
            render_agent_score_markdown(score)

    def test_missing_manifest_raises_error(self, tmp_path):
        runs_root, _manifest = _scaffold(tmp_path)
        ghost_manifest = tmp_path / "ghost.yaml"
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=ghost_manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="case_a"
                )
            ],
        )
        with pytest.raises(UnresolvedCitationError):
            render_agent_score_markdown(score)


class TestSectionOrdering:
    def test_sections_appear_in_canonical_order(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir,
                    [
                        _inconclusive_obs(
                            kind="must_call",
                            target="alpha",
                        ),
                    ],
                    case_id="case_a",
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        offsets = [
            markdown.find("# Agent evaluation report — "),
            markdown.find("## Summary"),
            markdown.find("## By assertion kind"),
            markdown.find("## By target"),
            markdown.find("## By case"),
            markdown.find("## Per-case detail"),
        ]
        assert all(o >= 0 for o in offsets)
        assert offsets == sorted(offsets)


class TestTrailingNewline:
    def test_output_ends_with_single_newline(
        self, tmp_path
    ):
        runs_root, manifest = _scaffold(tmp_path)
        case_dir = runs_root / "case-a"
        case_dir.mkdir()
        score = _build_agent_score(
            runs_root=runs_root,
            manifest_path=manifest,
            case_scores=[
                _build_case_score(
                    case_dir, [], case_id="case_a"
                )
            ],
        )
        markdown = render_agent_score_markdown(score)
        assert markdown.endswith("\n")
        assert not markdown.endswith("\n\n")
