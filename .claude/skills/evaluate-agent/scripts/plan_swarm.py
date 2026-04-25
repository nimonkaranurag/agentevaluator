#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.7", "pyyaml>=6"]
# ///
"""
Expand a validated manifest into a deterministic per-case fan-out plan.

Emits a JSON object to stdout describing every case the orchestrator must
dispatch. Each entry is self-contained: an absolute driver script path plus
the argv that drives one case under a shared run directory. The orchestrator
fans the entries out to N Claude sub-agents in parallel.

Exits 0 on success; 1 on any manifest load or validation error
(printed to stderr).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.manifest import (  # noqa: E402
    ManifestError,
    load_manifest,
)
from evaluate_agent.orchestration import (  # noqa: E402
    plan_swarm,
)


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="plan_swarm",
        description=(
            "Expand a validated agent manifest into a "
            "per-case fan-out plan. Emits JSON to stdout."
        ),
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the agent.yaml manifest.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("runs"),
        help=(
            "Directory where each case's run artifacts "
            "are written (default: ./runs). The plan "
            "resolves this to an absolute path so every "
            "sub-agent writes into the same directory "
            "regardless of its working directory."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    try:
        manifest = load_manifest(args.path)
    except ManifestError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    plan = plan_swarm(
        manifest,
        args.path,
        runs_root=args.runs_root,
    )
    print(plan.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
