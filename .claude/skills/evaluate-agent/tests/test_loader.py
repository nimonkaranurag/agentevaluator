"""Integration tests for the manifest loader.

Exercises file-read + YAML-parse + schema-validate end to end against real
fixture files on disk. Schema-specific invariants live in test_schema.py;
this module focuses on what only the loader adds (filesystem, YAML parse,
error wrapping)."""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.manifest.errors import (
    ManifestNotFoundError,
    ManifestSyntaxError,
    ManifestValidationError,
)
from evaluate_agent.manifest.loader import load_manifest

FIXTURES = Path(__file__).parent / "fixtures"


class TestValid:
    def test_loads_minimal_fixture(self) -> None:
        m = load_manifest(
            FIXTURES / "valid" / "minimal.yaml"
        )
        assert m.name == "minimal-agent"
        assert len(m.cases) == 1


class TestFileSystem:
    def test_missing_file_raises_not_found(self) -> None:
        with pytest.raises(ManifestNotFoundError):
            load_manifest(
                FIXTURES / "valid" / "does_not_exist.yaml"
            )

    def test_directory_raises_not_found(
        self, tmp_path: Path
    ) -> None:
        """A directory is not a file — surfaced the same as missing."""
        with pytest.raises(ManifestNotFoundError):
            load_manifest(tmp_path)


class TestSyntax:
    def test_malformed_yaml_raises_syntax_error(
        self,
    ) -> None:
        with pytest.raises(ManifestSyntaxError):
            load_manifest(
                FIXTURES / "invalid" / "bad_yaml.yaml"
            )

    def test_top_level_list_raises_syntax_error(
        self,
    ) -> None:
        with pytest.raises(
            ManifestSyntaxError, match="mapping"
        ):
            load_manifest(
                FIXTURES / "invalid" / "top_level_list.yaml"
            )


class TestValidation:
    def test_missing_name_raises_validation_error(
        self,
    ) -> None:
        with pytest.raises(
            ManifestValidationError
        ) as exc_info:
            load_manifest(
                FIXTURES / "invalid" / "missing_name.yaml"
            )
        assert "name" in str(exc_info.value)

    def test_error_message_enumerates_every_violation(
        self,
    ) -> None:
        """The formatted message must list all errors so a user fixing one
        at a time does not need to re-run validation to find the next.
        """
        with pytest.raises(
            ManifestValidationError
        ) as exc_info:
            load_manifest(
                FIXTURES
                / "invalid"
                / "multiple_errors.yaml"
            )
        msg = str(exc_info.value)
        assert msg.count("\n  - ") >= 2

    def test_validation_error_exposes_structured_cause(
        self,
    ) -> None:
        """The wrapped Pydantic error and the path are available for callers
        that want structured access, not just the formatted message.
        """
        path = FIXTURES / "invalid" / "missing_name.yaml"
        with pytest.raises(
            ManifestValidationError
        ) as exc_info:
            load_manifest(path)
        assert exc_info.value.cause is not None
        assert exc_info.value.path == path
