#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.7", "pyyaml>=6"]
# ///
"""
Recursively discover and validate agent manifests under a root directory.

Exits 0 when the discovery root is a directory and every discovered manifest
validates; exits 1 when the root is invalid or any discovered manifest fails
validation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.manifest import (  # noqa: E402
    DiscoveredManifest,
    DiscoveryFailure,
    DiscoveryOutcome,
    ManifestError,
    discover_manifests,
)


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="discover_manifests",
        description="Recursively discover and validate agent manifests under a root directory.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path("."),
        help="Directory under which to search for agent.yaml / *.agent.yaml (default: current directory).",
    )
    return parser.parse_args(argv)


_BUNDLED_EXAMPLES_DIR = (
    _SCRIPT_DIR.parent / "examples"
).resolve()


def _bundled_demo_manifest_paths() -> list[Path]:
    if not _BUNDLED_EXAMPLES_DIR.is_dir():
        return []
    return sorted(
        _BUNDLED_EXAMPLES_DIR.glob("*/agent.yaml")
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )

    try:
        outcomes = discover_manifests(args.root)
    except ManifestError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not outcomes:
        bundled = _bundled_demo_manifest_paths()
        print(
            f"No manifests found under {args.root}.\n"
            f"To proceed (pick one):\n"
            f"  - Drop an agent.yaml (or *.agent.yaml) into the directory and re-run.\n"
            f"  - Re-run discovery with a different root, e.g. a project subdirectory.\n"
            f"  - Use one of the bundled demo manifests shipped with this skill"
            f" (ask the user which one to evaluate before driving):\n"
            + (
                "".join(
                    f"      - {path}\n" for path in bundled
                )
                if bundled
                else ""
            )
            + f"  - Run /onboard-evaluate-agent to walk through writing"
            f" your own agent.yaml interactively (one field at a time, with"
            f" guidance on how to procure each value for whatever runtime"
            f" and observability stack the agent uses), then re-invoke"
            f" /evaluate-agent."
        )
        return 0

    valid = [
        o
        for o in outcomes
        if isinstance(o, DiscoveredManifest)
    ]
    invalid = [
        o
        for o in outcomes
        if isinstance(o, DiscoveryFailure)
    ]

    print(
        f"Discovered {len(outcomes)} manifest(s) under {args.root} "
        f"({len(valid)} valid, {len(invalid)} invalid)."
    )
    for outcome in outcomes:
        print()
        _print_outcome(outcome)

    if invalid:
        sys.stdout.flush()
        print(
            "\nTo proceed: fix every invalid manifest listed above and re-run discovery.",
            file=sys.stderr,
        )
        return 1
    return 0


def _print_outcome(
    outcome: DiscoveryOutcome,
) -> None:
    if isinstance(outcome, DiscoveredManifest):
        manifest = outcome.manifest
        description = manifest.description or "(none)"
        print(
            f"  [valid]    {outcome.path}\n"
            f"    name:         {manifest.name}\n"
            f"    description:  {description}\n"
            f"    cases:        {len(manifest.cases)}"
        )
    else:
        print(f"  [invalid]  {outcome.path}")
        for line in str(outcome.error).splitlines():
            print(f"    {line}")


if __name__ == "__main__":
    sys.exit(main())
