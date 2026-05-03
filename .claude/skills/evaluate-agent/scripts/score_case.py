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

Diagnostic logging (errors, warnings) is emitted on stderr in either
text or JSON form, controlled by --log-format.

Exits 0 when scoring completes (regardless of pass/fail/inconclusive
counts). Exits 1 on any manifest, case-selection, or case-directory
error (logged to stderr with the actionable recovery procedure embedded
in the message).

When --metrics PATH is supplied, the script writes a single JSON
document to PATH at completion that records per-phase wall-clock timing
(load_manifest, score_case), the script's exit status, and contextual
identifiers (manifest_path, case_id, case_dir).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.common.errors.manifest import (  # noqa: E402
    ManifestError,
)
from evaluate_agent.common.phase_metrics import (  # noqa: E402
    MetricsCollector,
)
from evaluate_agent.common.script_logging import (  # noqa: E402
    LOG_FORMATS,
    configure_script_logging,
)
from evaluate_agent.manifest import (  # noqa: E402
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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    logger = configure_script_logging(
        script_name="score_case",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(script_name="score_case")
    metrics.set_context(
        manifest_path=str(args.path),
        case_id=args.case,
        case_dir=str(args.case_dir),
    )
    exit_code = 1
    try:
        try:
            with metrics.phase("load_manifest"):
                manifest = load_manifest(args.path)
        except ManifestError as exc:
            logger.error(
                "Manifest failed to load: %s",
                exc,
                extra={"manifest_path": str(args.path)},
            )
            return 1

        case = next(
            (
                c
                for c in manifest.cases
                if c.id == args.case
            ),
            None,
        )
        if case is None:
            declared_ids = ", ".join(
                c.id for c in manifest.cases
            )
            logger.error(
                "Case %r is not declared in manifest "
                "%s.\n"
                "To proceed: re-invoke with --case set "
                "to one of the declared case ids, or "
                "add the case to the manifest's cases: "
                "list.\n"
                "Declared case ids: %s",
                args.case,
                args.path,
                declared_ids,
                extra={
                    "manifest_path": str(args.path),
                    "case_id": args.case,
                },
            )
            return 1

        case_dir = args.case_dir.resolve()
        if not case_dir.is_dir():
            logger.error(
                "Case directory does not exist or is "
                "not a directory: %s\n"
                "To proceed:\n"
                "  (1) Confirm the path matches the "
                "case directory the per-case driving "
                "procedure in SKILL.md wrote, namely "
                "<runs_root>/<agent>/<run_id>/"
                "<case_id>/. When plan_swarm.py was "
                "used, the directive's case_dir field "
                "is the authoritative path.\n"
                "  (2) Re-execute the per-case driving "
                "procedure (SKILL.md) against this "
                "manifest and case to capture artifacts "
                "under the case directory, or "
                "re-invoke score_case.py with a "
                "corrected --case-dir path.",
                case_dir,
                extra={
                    "case_id": args.case,
                    "case_dir": str(case_dir),
                },
            )
            return 1

        with metrics.phase("score_case"):
            score = score_case(
                case=case,
                case_dir=case_dir,
                max_dom_bytes=manifest.interaction.max_dom_bytes,
            )
        print(score.model_dump_json(indent=2))
        exit_code = 0
        return exit_code
    finally:
        metrics.emit_if_configured(
            args.metrics,
            exit_status=(
                "success" if exit_code == 0 else "error"
            ),
        )


if __name__ == "__main__":
    sys.exit(main())
