"""
Failure-mode tests for load_manifest and discover_manifests, including the apiVersion gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evaluate_agent.common.errors.manifest import (
    ManifestDiscoveryRootError,
    ManifestMissingApiVersionError,
    ManifestNotFoundError,
    ManifestSyntaxError,
    ManifestUnsupportedApiVersionError,
    ManifestValidationError,
)
from evaluate_agent.manifest.api_version import (
    CURRENT_API_VERSION,
    SUPPORTED_API_VERSIONS,
)
from evaluate_agent.manifest.discovery import (
    DiscoveredManifest,
    DiscoveryFailure,
    discover_manifests,
)
from evaluate_agent.manifest.loader import load_manifest

_VALID_BODY = """\
apiVersion: agentevaluator/v1
name: demo
access:
  url: https://example.com/chat
cases:
  - id: only
    input: hello
    assertions:
      final_response_contains: world
"""


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_loader_raises_not_found_for_missing_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(ManifestNotFoundError):
        load_manifest(tmp_path / "nope.yaml")


def test_loader_raises_syntax_error_on_bad_yaml(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "agent.yaml", "key: : :")
    with pytest.raises(ManifestSyntaxError) as info:
        load_manifest(path)
    assert "malformed" in str(info.value).lower()


def test_loader_raises_syntax_error_for_top_level_list(
    tmp_path: Path,
) -> None:
    # A YAML document parsing to a list (not a mapping) bypasses
    # apiVersion gating; the loader must reject before Pydantic
    # produces a confusing nested-error stack.
    path = _write(tmp_path / "agent.yaml", "- a\n- b\n")
    with pytest.raises(ManifestSyntaxError) as info:
        load_manifest(path)
    assert "mapping" in str(info.value)


def test_loader_raises_missing_api_version(
    tmp_path: Path,
) -> None:
    body = _VALID_BODY.replace(
        "apiVersion: agentevaluator/v1\n", ""
    )
    path = _write(tmp_path / "agent.yaml", body)
    with pytest.raises(ManifestMissingApiVersionError):
        load_manifest(path)


def test_loader_raises_unsupported_api_version(
    tmp_path: Path,
) -> None:
    body = _VALID_BODY.replace(
        "agentevaluator/v1", "agentevaluator/v999"
    )
    path = _write(tmp_path / "agent.yaml", body)
    with pytest.raises(
        ManifestUnsupportedApiVersionError
    ) as info:
        load_manifest(path)
    assert "agentevaluator/v999" in str(info.value)
    assert sorted(SUPPORTED_API_VERSIONS)[0] in str(
        info.value
    )


def test_loader_raises_validation_error_with_field_paths(
    tmp_path: Path,
) -> None:
    # Multiple violations in one manifest must surface every
    # offender in the formatted message — operators want one
    # round trip per fix-cycle, not one per violation.
    bad = (
        f"apiVersion: {CURRENT_API_VERSION}\n"
        "name: demo\n"
        "access:\n"
        "  url: ftp://nope\n"
        "cases: []\n"
    )
    path = _write(tmp_path / "agent.yaml", bad)
    with pytest.raises(ManifestValidationError) as info:
        load_manifest(path)
    detail = str(info.value)
    assert "access.url" in detail
    assert "cases" in detail


def test_loader_returns_validated_manifest(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "agent.yaml", _VALID_BODY)
    manifest = load_manifest(path)
    assert manifest.name == "demo"
    assert manifest.cases[0].id == "only"


def test_discovery_rejects_non_directory_root(
    tmp_path: Path,
) -> None:
    not_a_dir = tmp_path / "agent.yaml"
    not_a_dir.write_text(_VALID_BODY, encoding="utf-8")
    with pytest.raises(ManifestDiscoveryRootError):
        discover_manifests(not_a_dir)


def test_discovery_finds_agent_yaml_at_multiple_depths(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "agent.yaml", _VALID_BODY)
    _write(
        tmp_path / "deep" / "nested" / "agent.yaml",
        _VALID_BODY,
    )
    _write(
        tmp_path / "alt" / "first.agent.yaml", _VALID_BODY
    )
    outcomes = discover_manifests(tmp_path)
    assert len(outcomes) == 3
    assert all(
        isinstance(o, DiscoveredManifest) for o in outcomes
    )


def test_discovery_skips_hidden_directories(
    tmp_path: Path,
) -> None:
    # Hidden dirs (.git, .venv) routinely contain unrelated
    # YAML; descending into them would surface noise. The
    # walker must skip every dotfile-prefixed directory.
    _write(tmp_path / "agent.yaml", _VALID_BODY)
    _write(tmp_path / ".venv" / "agent.yaml", _VALID_BODY)
    _write(tmp_path / ".git" / "agent.yaml", _VALID_BODY)
    outcomes = discover_manifests(tmp_path)
    assert len(outcomes) == 1
    only = outcomes[0]
    assert isinstance(only, DiscoveredManifest)
    assert only.path == tmp_path / "agent.yaml"


def test_discovery_reports_failures_alongside_successes(
    tmp_path: Path,
) -> None:
    # A bad manifest must not abort the walk — every reachable
    # file is reported with its outcome so the operator can fix
    # all of them in one pass.
    _write(tmp_path / "good" / "agent.yaml", _VALID_BODY)
    _write(
        tmp_path / "bad" / "agent.yaml",
        "apiVersion: agentevaluator/v1\nname: x\n",
    )
    outcomes = discover_manifests(tmp_path)
    by_kind = {type(o).__name__: o for o in outcomes}
    assert "DiscoveredManifest" in by_kind
    assert "DiscoveryFailure" in by_kind
    failure = by_kind["DiscoveryFailure"]
    assert isinstance(failure, DiscoveryFailure)
    assert isinstance(
        failure.error, ManifestValidationError
    )


def test_discovery_returns_outcomes_sorted_by_path(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "z" / "agent.yaml", _VALID_BODY)
    _write(tmp_path / "a" / "agent.yaml", _VALID_BODY)
    outcomes = discover_manifests(tmp_path)
    paths = [o.path for o in outcomes]
    assert paths == sorted(paths)
