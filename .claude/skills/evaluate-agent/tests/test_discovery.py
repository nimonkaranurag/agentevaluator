"""Tests for recursive manifest discovery.

Exercises the filesystem walk, glob-pattern coverage, hidden-directory
filtering, per-manifest validation outcomes, and deterministic ordering.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.manifest import (
    DiscoveredManifest,
    DiscoveryFailure,
    ManifestDiscoveryRootError,
    ManifestSyntaxError,
    ManifestValidationError,
    discover_manifests,
)

_VALID_MANIFEST = """\
name: {name}
access:
  url: https://example.com/
cases:
  - id: only_case
    input: "hi"
"""

_MISSING_NAME = """\
access:
  url: https://example.com/
cases:
  - id: only_case
    input: "hi"
"""

_MALFORMED_YAML = "name: [unterminated\n"


def _write_valid(
    path: Path, name: str = "valid-agent"
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_VALID_MANIFEST.format(name=name))


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestEmptyAndTrivial:
    def test_empty_directory_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        assert discover_manifests(tmp_path) == []

    def test_directory_with_unrelated_files_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "README.md").write_text("x")
        (tmp_path / "config.yaml").write_text(
            "key: value\n"
        )
        assert discover_manifests(tmp_path) == []


class TestFindsManifests:
    def test_finds_agent_yaml_at_root(
        self, tmp_path: Path
    ) -> None:
        _write_valid(tmp_path / "agent.yaml")

        outcomes = discover_manifests(tmp_path)

        assert len(outcomes) == 1
        assert isinstance(outcomes[0], DiscoveredManifest)
        assert outcomes[0].path == tmp_path / "agent.yaml"
        assert outcomes[0].manifest.name == "valid-agent"

    def test_finds_nested_agent_yaml(
        self, tmp_path: Path
    ) -> None:
        _write_valid(
            tmp_path / "a" / "b" / "agent.yaml",
            name="deep-agent",
        )

        outcomes = discover_manifests(tmp_path)

        assert len(outcomes) == 1
        assert isinstance(outcomes[0], DiscoveredManifest)
        assert outcomes[0].manifest.name == "deep-agent"

    def test_finds_dot_agent_yaml_pattern(
        self, tmp_path: Path
    ) -> None:
        _write_valid(
            tmp_path / "flight.agent.yaml",
            name="flight-agent",
        )
        _write_valid(
            tmp_path / "refund.agent.yaml",
            name="refund-agent",
        )

        outcomes = discover_manifests(tmp_path)

        names = [
            o.manifest.name
            for o in outcomes
            if isinstance(o, DiscoveredManifest)
        ]
        assert names == [
            "flight-agent",
            "refund-agent",
        ]

    def test_finds_both_patterns_without_duplicates(
        self, tmp_path: Path
    ) -> None:
        _write_valid(
            tmp_path / "agent.yaml",
            name="unnamed-agent",
        )
        _write_valid(
            tmp_path / "extra.agent.yaml",
            name="extra-agent",
        )

        outcomes = discover_manifests(tmp_path)

        paths = [o.path for o in outcomes]
        assert paths == sorted(paths)
        assert len(paths) == len(set(paths))
        assert len(outcomes) == 2


class TestHiddenDirectoriesAreSkipped:
    def test_manifests_under_hidden_dirs_are_not_discovered(
        self, tmp_path: Path
    ) -> None:
        _write_valid(tmp_path / ".venv" / "agent.yaml")
        _write_valid(
            tmp_path / ".git" / "hooks" / "agent.yaml"
        )
        _write_valid(
            tmp_path / "visible" / "agent.yaml",
            name="visible-agent",
        )

        outcomes = discover_manifests(tmp_path)

        assert len(outcomes) == 1
        assert isinstance(outcomes[0], DiscoveredManifest)
        assert outcomes[0].manifest.name == "visible-agent"

    def test_root_starting_with_dot_is_still_scanned(
        self, tmp_path: Path
    ) -> None:
        """The hidden-dir filter applies to descendants, not the root."""
        hidden_root = tmp_path / ".scratch"
        _write_valid(hidden_root / "agent.yaml")

        outcomes = discover_manifests(hidden_root)

        assert len(outcomes) == 1


class TestFailureOutcomes:
    def test_validation_failure_is_captured_not_raised(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "agent.yaml"
        _write_text(path, _MISSING_NAME)

        outcomes = discover_manifests(tmp_path)

        assert len(outcomes) == 1
        assert isinstance(outcomes[0], DiscoveryFailure)
        assert outcomes[0].path == path
        assert isinstance(
            outcomes[0].error,
            ManifestValidationError,
        )

    def test_syntax_failure_is_captured_not_raised(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "agent.yaml"
        _write_text(path, _MALFORMED_YAML)

        outcomes = discover_manifests(tmp_path)

        assert len(outcomes) == 1
        assert isinstance(outcomes[0], DiscoveryFailure)
        assert isinstance(
            outcomes[0].error, ManifestSyntaxError
        )

    def test_mix_of_valid_and_invalid_is_interleaved(
        self, tmp_path: Path
    ) -> None:
        _write_valid(
            tmp_path / "a" / "agent.yaml",
            name="a-agent",
        )
        _write_text(
            tmp_path / "b" / "agent.yaml",
            _MISSING_NAME,
        )
        _write_valid(
            tmp_path / "c" / "agent.yaml",
            name="c-agent",
        )

        outcomes = discover_manifests(tmp_path)

        assert len(outcomes) == 3
        kinds = [type(o).__name__ for o in outcomes]
        assert kinds == [
            "DiscoveredManifest",
            "DiscoveryFailure",
            "DiscoveredManifest",
        ]


class TestOrdering:
    def test_outcomes_sorted_by_path(
        self, tmp_path: Path
    ) -> None:
        _write_valid(
            tmp_path / "z" / "agent.yaml", name="z"
        )
        _write_valid(
            tmp_path / "a" / "agent.yaml", name="a"
        )
        _write_valid(
            tmp_path / "m" / "agent.yaml", name="m"
        )

        outcomes = discover_manifests(tmp_path)

        paths = [o.path for o in outcomes]
        assert paths == sorted(paths)


class TestRootErrors:
    def test_missing_root_raises_discovery_root_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(ManifestDiscoveryRootError):
            discover_manifests(tmp_path / "does_not_exist")

    def test_file_as_root_raises_discovery_root_error(
        self, tmp_path: Path
    ) -> None:
        not_a_dir = tmp_path / "file.txt"
        not_a_dir.write_text("x")
        with pytest.raises(ManifestDiscoveryRootError):
            discover_manifests(not_a_dir)


class TestSymlinkSafety:
    def test_symlinked_subdirectories_are_not_followed(
        self, tmp_path: Path
    ) -> None:
        real = tmp_path / "real"
        _write_valid(real / "agent.yaml", name="real-agent")
        link = tmp_path / "link"
        link.symlink_to(real, target_is_directory=True)

        outcomes = discover_manifests(tmp_path)

        paths = [o.path for o in outcomes]
        assert paths == [real / "agent.yaml"]
