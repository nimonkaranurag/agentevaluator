"""
Tests for the render_report.py CLI shell.

Exercises main() in-process so we hit the autodetect, validation, and
error-message paths without spawning a subprocess.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from evaluate_agent.scoring import (
    AssertionEvidence,
    AssertionPassed,
    CaseScore,
    score_agent,
)

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "render_report.py"
)


@pytest.fixture(scope="module")
def render_report_main() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "render_report_under_test", _SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_evidence(case_dir: Path) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    artifact = case_dir / "step-001-landing.html"
    artifact.write_text("<html></html>", encoding="utf-8")
    return artifact


def _build_case_score(
    case_dir: Path,
    *,
    case_id: str = "happy_case",
) -> CaseScore:
    artifact = _seed_evidence(case_dir)
    return CaseScore(
        case_id=case_id,
        case_dir=case_dir,
        outcomes=(
            AssertionPassed(
                assertion_kind=("final_response_contains"),
                evidence=AssertionEvidence(
                    artifact_path=artifact,
                ),
            ),
        ),
    )


def _write_case_score_json(
    tmp_path: Path,
) -> tuple[Path, Path]:
    case_dir = tmp_path / "case-a"
    score = _build_case_score(case_dir)
    score_path = tmp_path / "case_score.json"
    score_path.write_text(
        score.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return score_path, case_dir


def _write_agent_score_json(
    tmp_path: Path,
) -> Path:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    manifest = tmp_path / "agent.yaml"
    manifest.write_text("stub", encoding="utf-8")
    case_dir = runs_root / "case-a"
    score = score_agent(
        case_scores=(
            _build_case_score(case_dir, case_id="case_a"),
        ),
        agent_name="autodetect_agent",
        run_id="20260425T173000Z",
        runs_root=runs_root,
        manifest_path=manifest,
    )
    score_path = tmp_path / "agent_score.json"
    score_path.write_text(
        score.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return score_path


class TestAutodetect:
    def test_case_score_renders_h1_case_header(
        self, render_report_main, tmp_path, capsys
    ):
        score_path, _case_dir = _write_case_score_json(
            tmp_path
        )
        exit_code = render_report_main.main(
            [str(score_path)]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.startswith(
            "# Case `happy_case`"
        )

    def test_agent_score_renders_h1_agent_header(
        self, render_report_main, tmp_path, capsys
    ):
        score_path = _write_agent_score_json(tmp_path)
        exit_code = render_report_main.main(
            [str(score_path)]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.startswith(
            "# Agent evaluation report — "
            "`autodetect_agent`"
        )

    def test_agent_score_includes_per_case_detail(
        self, render_report_main, tmp_path, capsys
    ):
        score_path = _write_agent_score_json(tmp_path)
        render_report_main.main([str(score_path)])
        captured = capsys.readouterr()
        assert "## Per-case detail" in captured.out
        assert "### Case `case_a`" in captured.out


class TestExitCodes:
    def test_success_returns_zero(
        self, render_report_main, tmp_path, capsys
    ):
        score_path, _case_dir = _write_case_score_json(
            tmp_path
        )
        assert (
            render_report_main.main([str(score_path)]) == 0
        )

    def test_missing_file_returns_one(
        self, render_report_main, tmp_path, capsys
    ):
        ghost = tmp_path / "never_written.json"
        exit_code = render_report_main.main([str(ghost)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert (
            "does not exist or is not a file"
            in captured.err
        )
        assert "To proceed:" in captured.err

    def test_malformed_json_returns_one(
        self, render_report_main, tmp_path, capsys
    ):
        score_path = tmp_path / "broken.json"
        score_path.write_text("{not json", encoding="utf-8")
        exit_code = render_report_main.main(
            [str(score_path)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "valid JSON" in captured.err

    def test_top_level_array_returns_one(
        self, render_report_main, tmp_path, capsys
    ):
        score_path = tmp_path / "array.json"
        score_path.write_text("[]", encoding="utf-8")
        exit_code = render_report_main.main(
            [str(score_path)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "JSON object" in captured.err

    def test_invalid_case_score_returns_one(
        self, render_report_main, tmp_path, capsys
    ):
        score_path = tmp_path / "broken_case.json"
        score_path.write_text(
            '{"case_id": "x"}', encoding="utf-8"
        )
        exit_code = render_report_main.main(
            [str(score_path)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert (
            "validate against the CaseScore schema"
            in captured.err
        )

    def test_invalid_agent_score_returns_one(
        self, render_report_main, tmp_path, capsys
    ):
        score_path = tmp_path / "broken_agent.json"
        score_path.write_text(
            '{"agent_name": "x"}',
            encoding="utf-8",
        )
        exit_code = render_report_main.main(
            [str(score_path)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert (
            "validate against the AgentScore schema"
            in captured.err
        )

    def test_unresolved_citation_returns_one(
        self, render_report_main, tmp_path, capsys
    ):
        case_dir = tmp_path / "case-a"
        case_dir.mkdir()
        ghost_artifact = case_dir / "ghost.html"
        score = CaseScore(
            case_id="ghost_case",
            case_dir=case_dir,
            outcomes=(
                AssertionPassed(
                    assertion_kind=(
                        "final_response_contains"
                    ),
                    evidence=AssertionEvidence(
                        artifact_path=ghost_artifact,
                    ),
                ),
            ),
        )
        score_path = tmp_path / "score.json"
        score_path.write_text(
            score.model_dump_json(indent=2),
            encoding="utf-8",
        )
        exit_code = render_report_main.main(
            [str(score_path)]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "do not resolve on disk" in captured.err
        assert "To proceed:" in captured.err


class TestStdoutBoundary:
    def test_success_emits_to_stdout_only(
        self, render_report_main, tmp_path, capsys
    ):
        score_path, _ = _write_case_score_json(tmp_path)
        render_report_main.main([str(score_path)])
        captured = capsys.readouterr()
        assert captured.out
        assert captured.err == ""

    def test_failure_emits_to_stderr_only(
        self, render_report_main, tmp_path, capsys
    ):
        ghost = tmp_path / "never.json"
        render_report_main.main([str(ghost)])
        captured = capsys.readouterr()
        assert captured.err
        assert captured.out == ""
