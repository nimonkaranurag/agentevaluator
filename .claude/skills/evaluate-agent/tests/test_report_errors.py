"""
Tests for the UnresolvedCitationError exception class.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.report import (
    CitationValidationFailure,
    UnresolvedCitationError,
)


def _failure(
    *,
    score_path: str = "outcomes[0].evidence.artifact_path",
    artifact_path: Path = Path("/tmp/ghost.html"),
    expected_kind: str = "file",
) -> CitationValidationFailure:
    return CitationValidationFailure(
        score_path=score_path,
        artifact_path=artifact_path,
        expected_kind=expected_kind,
    )


class TestConstruction:
    def test_failures_attribute_round_trips(self):
        failures = (_failure(), _failure(score_path="x"))
        error = UnresolvedCitationError(failures)
        assert error.failures == failures

    def test_empty_failures_rejected(self):
        with pytest.raises(ValueError):
            UnresolvedCitationError(())


class TestErrorMessage:
    def test_message_leads_with_failure_count(self):
        error = UnresolvedCitationError(
            (
                _failure(),
                _failure(score_path="manifest_path"),
                _failure(score_path="runs_root"),
            )
        )
        assert (
            "3 citation(s) inside the score record"
            in str(error)
        )

    def test_each_failure_renders_score_path(self):
        error = UnresolvedCitationError(
            (
                _failure(
                    score_path="case_dir",
                    expected_kind="directory",
                ),
                _failure(
                    score_path=(
                        "outcomes[1].evidence."
                        "artifact_path"
                    ),
                ),
            )
        )
        text = str(error)
        assert "case_dir:" in text
        assert "outcomes[1].evidence.artifact_path:" in text

    def test_each_failure_renders_expected_kind(self):
        error = UnresolvedCitationError(
            (
                _failure(
                    expected_kind="directory",
                ),
                _failure(expected_kind="file"),
            )
        )
        text = str(error)
        assert "(expected: directory)" in text
        assert "(expected: file)" in text

    def test_message_includes_recovery_procedure(self):
        error = UnresolvedCitationError((_failure(),))
        text = str(error)
        assert "To proceed:" in text
        assert "render_report.py" in text
        assert "score_case.py" in text
        assert "score_agent.py" in text

    def test_message_numbers_failures_starting_at_one(
        self,
    ):
        error = UnresolvedCitationError(
            (
                _failure(score_path="alpha"),
                _failure(score_path="beta"),
            )
        )
        text = str(error)
        alpha_offset = text.find("(1) alpha")
        beta_offset = text.find("(2) beta")
        assert alpha_offset > 0
        assert beta_offset > alpha_offset


class TestExceptionContract:
    def test_is_a_subclass_of_exception(self):
        assert issubclass(
            UnresolvedCitationError, Exception
        )

    def test_can_be_caught_as_exception(self):
        with pytest.raises(Exception):
            raise UnresolvedCitationError((_failure(),))

    def test_args_carry_formatted_message(self):
        error = UnresolvedCitationError((_failure(),))
        assert error.args[0] == str(error)
