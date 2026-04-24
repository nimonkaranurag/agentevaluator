"""
Recursive discovery and validation of agent manifests under a directory tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import (
    ManifestDiscoveryRootError,
    ManifestError,
)
from .loader import load_manifest
from .schema import AgentManifest

_MANIFEST_GLOBS: tuple[str, ...] = (
    "agent.yaml",
    "*.agent.yaml",
)


@dataclass(frozen=True)
class DiscoveredManifest:
    path: Path
    manifest: AgentManifest


@dataclass(frozen=True)
class DiscoveryFailure:
    path: Path
    error: ManifestError


DiscoveryOutcome = DiscoveredManifest | DiscoveryFailure


def discover_manifests(
    root: Path,
) -> list[DiscoveryOutcome]:
    if not root.is_dir():
        raise ManifestDiscoveryRootError(root)

    outcomes: list[DiscoveryOutcome] = []
    for path in _walk_manifest_files(root):
        try:
            manifest = load_manifest(path)
        except ManifestError as exc:
            outcomes.append(
                DiscoveryFailure(path=path, error=exc)
            )
        else:
            outcomes.append(
                DiscoveredManifest(
                    path=path, manifest=manifest
                )
            )
    outcomes.sort(key=lambda o: o.path)
    return outcomes


def _walk_manifest_files(
    root: Path,
) -> list[Path]:
    seen: set[Path] = set()
    for directory in _iter_non_hidden_dirs(root):
        for pattern in _MANIFEST_GLOBS:
            for candidate in directory.glob(pattern):
                if candidate.is_file():
                    seen.add(candidate)
    return sorted(seen)


def _iter_non_hidden_dirs(
    root: Path,
):
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        yield current
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if (
                child.is_dir()
                and not child.is_symlink()
                and not child.name.startswith(".")
            ):
                stack.append(child)


__all__ = [
    "DiscoveredManifest",
    "DiscoveryFailure",
    "DiscoveryOutcome",
    "discover_manifests",
]
