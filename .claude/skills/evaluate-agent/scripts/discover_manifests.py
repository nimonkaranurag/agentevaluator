#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.7", "pyyaml>=6"]
# ///
"""
Recursively discover and validate agent manifests under a root directory.

Scans the supplied root for agent.yaml / *.agent.yaml files, validates
each one against the manifest schema, and prints a per-manifest summary
on stdout (valid vs invalid). Diagnostic logging (errors, warnings) is
emitted on stderr in either text or JSON form, controlled by
--log-format.

Exits 0 when the discovery root is a directory and every discovered
manifest validates; exits 1 when the root is invalid or any discovered
manifest fails validation (the offending manifest's error is printed on
stdout in the per-manifest summary; the overall failure pointer is
logged to stderr).

When --metrics PATH is supplied, the script writes a single JSON
document to PATH at completion that records per-phase wall-clock timing
(discover) and the script's exit status.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.common.phase_metrics import (  # noqa: E402
    MetricsCollector,
)
from evaluate_agent.common.script_logging import (  # noqa: E402
    LOG_FORMATS,
    configure_script_logging,
)
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
    parser.add_argument(
        "--log-format",
        choices=LOG_FORMATS,
        default="text",
        help=(
            "Format for diagnostic log records on "
            "stderr. Default: text. CI consumers "
            "should select json."
        ),
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=None,
        help=(
            "Path to write the per-phase timing JSON "
            "document to at script completion. Omit "
            "to skip metrics emission."
        ),
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
    logger = configure_script_logging(
        script_name="discover_manifests",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(
        script_name="discover_manifests"
    )
    exit_code = 1
    try:
        try:
            with metrics.phase("discover"):
                outcomes = discover_manifests(args.root)
        except ManifestError as exc:
            logger.error("Discovery aborted: %s", exc)
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
                        f"      - {path}\n"
                        for path in bundled
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
            exit_code = 0
            return exit_code

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
            logger.error(
                "Fix every invalid manifest listed "
                "in the discovery output above and "
                "re-run discovery."
            )
            return 1
        exit_code = 0
        return exit_code
    finally:
        metrics.emit_if_configured(
            args.metrics,
            exit_status=(
                "success" if exit_code == 0 else "error"
            ),
        )


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
