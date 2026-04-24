#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.7", "pyyaml>=6"]
# ///
"""
Validate an agent manifest.

Exits 0 on success; 1 on any load or validation error (printed to stderr).
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


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="validate_manifest",
        description="Validate an agentevaluator agent manifest.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the agent.yaml file.",
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

    print(
        f"OK: Manifest is well-formed.\n"
        f"  path:             {args.path}\n"
        f"  agent:            {manifest.name}\n"
        f"  cases:            {len(manifest.cases)}\n"
        f"  tools declared:   {len(manifest.tools_catalog)}\n"
        f"  agents declared:  {len(manifest.agents_catalog)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
