#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4>=4.12",
#     "pydantic>=2.7",
#     "pyyaml>=6",
# ]
# ///
"""
Score one captured case against its declared assertions.

Reads the case from a validated agent.yaml manifest, evaluates each
declared assertion against artifacts under the supplied case directory,
and emits a JSON CaseScore record to stdout. Every passed or failed
outcome cites a real artifact path; every inconclusive outcome names the
evidence it required and how to make it available on a subsequent run.

Exits 0 when scoring completes (regardless of pass/fail/inconclusive
counts). Exits 1 on any manifest, case-selection, or case-directory
error printed to stderr.
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
from evaluate_agent.scoring import (  # noqa: E402
    score_case,
)


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="score_case",
        description=(
            "Score one captured case against its "
            "declared assertions and emit a JSON record "
            "to stdout."
        ),
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the agent.yaml manifest.",
    )
    parser.add_argument(
        "--case",
        required=True,
        help=(
            "Id of the case (under manifest.cases) to "
            "score."
        ),
    )
    parser.add_argument(
        "--case-dir",
        required=True,
        type=Path,
        help=(
            "Absolute path to the case directory "
            "written by the per-case driving "
            "procedure in SKILL.md "
            "(<runs-root>/<agent>/<run-id>/<case-id>). "
            "Outcomes cite artifacts under this path."
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

    case = next(
        (c for c in manifest.cases if c.id == args.case),
        None,
    )
    if case is None:
        declared_ids = ", ".join(
            c.id for c in manifest.cases
        )
        print(
            f"Case {args.case!r} is not declared in "
            f"manifest {args.path}.\n"
            f"To proceed: re-invoke with --case set to "
            f"one of the declared case ids, or add the "
            f"case to the manifest's cases: list.\n"
            f"Declared case ids: {declared_ids}",
            file=sys.stderr,
        )
        return 1

    case_dir = args.case_dir.resolve()
    if not case_dir.is_dir():
        print(
            f"Case directory does not exist or is not "
            f"a directory: {case_dir}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path matches the case "
            f"directory the per-case driving procedure "
            f"in SKILL.md wrote, namely "
            f"<runs_root>/<agent>/<run_id>/<case_id>/. "
            f"When plan_swarm.py was used, the "
            f"directive's case_dir field is the "
            f"authoritative path.\n"
            f"  (2) Re-execute the per-case driving "
            f"procedure (SKILL.md) against this manifest "
            f"and case to capture artifacts under the "
            f"case directory, or re-invoke score_case.py "
            f"with a corrected --case-dir path.",
            file=sys.stderr,
        )
        return 1

    score = score_case(case=case, case_dir=case_dir)
    print(score.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
