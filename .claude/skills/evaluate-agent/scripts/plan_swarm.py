#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.7", "pyyaml>=6"]
# ///
"""
Expand a validated manifest into a deterministic per-case fan-out plan.

Emits a JSON SwarmPlan to stdout. Each directive in plan.directives is a
self-contained brief for one Claude sub-agent: the URL to navigate to,
preconditions, the case input, and the absolute paths the sub-agent
writes its landing + post-submit screenshots and DOM snapshots to.
Every directive shares the same run_id so all sub-agents land artifacts
in one run directory. The orchestrator fans the directives out in a
single message so each sub-agent gets its own isolated Playwright MCP
browser.

Diagnostic logging (errors, warnings) is emitted on stderr in either
text or JSON form, controlled by --log-format.

Exits 0 on success; 1 on any manifest load or validation error (logged
to stderr with the actionable recovery procedure embedded in the
message).

When --metrics PATH is supplied, the script writes a single JSON
document to PATH at completion that records per-phase wall-clock timing
(load_manifest, plan_swarm), the script's exit status, and contextual
identifiers (manifest_path, run_id).
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
        script_name="plan_swarm",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(script_name="plan_swarm")
    metrics.set_context(manifest_path=str(args.path))
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

        with metrics.phase("plan_swarm"):
            plan = plan_swarm(
                manifest,
                args.path,
                runs_root=args.runs_root,
            )
        metrics.set_context(run_id=plan.run_id)
        print(plan.model_dump_json(indent=2))
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
