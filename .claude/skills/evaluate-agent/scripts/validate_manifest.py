#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.7", "pyyaml>=6"]
# ///
"""
Validate an agent manifest.

Reads an agent.yaml file from the supplied path, validates it against the
manifest schema, and prints a formal success block on stdout when the
manifest is well-formed. Diagnostic logging (errors, warnings) is emitted
on stderr in either text or JSON form, controlled by --log-format.

Exits 0 on success; 1 on any load or validation error (logged to stderr
with the actionable recovery procedure embedded in the message).

When --metrics PATH is supplied, the script writes a single JSON document
to PATH at completion that records per-phase wall-clock timing
(load_manifest), the script's exit status, and contextual identifiers
(manifest_path).
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
        script_name="validate_manifest",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(
        script_name="validate_manifest"
    )
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

        print(
            f"OK: Manifest is well-formed.\n"
            f"  path:             {args.path}\n"
            f"  agent:            {manifest.name}\n"
            f"  cases:            {len(manifest.cases)}\n"
            f"  tools declared:   {len(manifest.tools_catalog)}\n"
            f"  agents declared:  {len(manifest.agents_catalog)}"
        )
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
