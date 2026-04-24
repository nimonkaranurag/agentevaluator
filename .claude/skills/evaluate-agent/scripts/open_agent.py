#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pydantic>=2.7",
#     "pyyaml>=6",
#     "playwright>=1.48",
# ]
# ///
"""
Open a live web agent and capture a landing screenshot for one declared case.

Exits 0 on success; 1 on any manifest, auth, or driver error (printed to stderr).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.driver import (  # noqa: E402
    Capture,
    MissingAuthEnvVar,
    RunArtifactLayout,
    open_session,
)
from evaluate_agent.manifest import (  # noqa: E402
    ManifestError,
    load_manifest,
)


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="open_agent",
        description="Open a live web agent and capture a landing screenshot for one declared case.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the agent.yaml manifest.",
    )
    parser.add_argument(
        "--case",
        required=True,
        help="Id of the case (under manifest.cases) to associate this run with.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("runs"),
        help="Directory where run artifacts are written (default: ./runs).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window (default: headless).",
    )
    return parser.parse_args(argv)


async def _drive(
    args: argparse.Namespace,
) -> int:
    try:
        manifest = load_manifest(args.path)
    except ManifestError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    case = next(
        (c for c in manifest.cases if c.id == args.case),
        None,
    )
    if case is None:
        declared_ids = ", ".join(
            c.id for c in manifest.cases
        )
        print(
            f"Case {args.case!r} is not declared in manifest {args.path}.\n"
            f"To proceed: re-invoke with --case set to one of the declared case ids, "
            f"or add the case to the manifest's cases: list.\n"
            f"Declared case ids: {declared_ids}",
            file=sys.stderr,
        )
        return 1

    layout = RunArtifactLayout.for_agent(
        agent_name=manifest.name,
        runs_root=args.runs_root,
    )
    capture = Capture(layout=layout, case_id=case.id)

    try:
        async with open_session(
            manifest.access,
            headless=not args.headed,
        ) as page:
            screenshot = await capture.screenshot(
                page, "landing"
            )
    except MissingAuthEnvVar as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"OK: Landing capture complete.\n"
        f"  agent:               {manifest.name}\n"
        f"  case:                {case.id}\n"
        f"  run_dir:             {layout.run_dir}\n"
        f"  landing_screenshot:  {screenshot}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    return asyncio.run(_drive(args))


if __name__ == "__main__":
    sys.exit(main())
