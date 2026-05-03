#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4>=4.12",
#     "langfuse>=3",
#     "pydantic>=2.7",
#     "pyyaml>=6",
# ]
# ///
"""
Fetch upstream observability traces and write them to the standard format.

Reads manifest.observability.langfuse, queries the declared LangFuse host
for traces matching the case (filtered by session_id and an optional
time window), maps each trace's observations to the on-disk
observability schema (TOOL -> tool_calls.jsonl, AGENT ->
routing_decisions.jsonl, GENERATION count -> step_count.json), and
persists them under <case-dir>/trace/observability/.

Diagnostic logging (errors, warnings) is emitted on stderr in either
text or JSON form, controlled by --log-format.

Exits 0 once the fetch completes (regardless of trace or observation
count). Exits 1 on any manifest, case-selection, case-directory,
credential, or LangFuse query error (logged to stderr with the
actionable recovery procedure embedded in the message).

When --metrics PATH is supplied, the script writes a single JSON
document to PATH at completion that records per-phase wall-clock timing
(load_manifest, fetch_observability), the script's exit status, and
contextual identifiers (manifest_path, case_id, case_dir).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.common.errors.observability_fetcher import (  # noqa: E402
    LangfuseSourceNotDeclared,
    ObservabilityFetcherError,
)
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
from evaluate_agent.observability_fetcher import (  # noqa: E402
    FetchedObservability,
    fetch_langfuse_observability,
)


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fetch_observability",
        description=(
            "Fetch LangFuse traces for one captured "
            "case and persist them as the standard "
            "on-disk observability logs."
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
            "Id of the case (under manifest.cases) the "
            "fetched observability belongs to."
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
            "The fetched observability artifacts are "
            "written under <case-dir>/trace/"
            "observability/."
        ),
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "LangFuse session_id to filter traces by. "
            "Default: the case id. The agent under "
            "evaluation must instrument its LangFuse "
            "traces with this session_id for the "
            "fetcher to find them."
        ),
    )
    parser.add_argument(
        "--since",
        default=None,
        type=_parse_iso_timestamp,
        help=(
            "ISO-8601 lower bound on trace timestamps "
            "(inclusive). Narrows the LangFuse query "
            "when the same session_id has been used "
            "across multiple runs. Default: no lower "
            "bound."
        ),
    )
    parser.add_argument(
        "--until",
        default=None,
        type=_parse_iso_timestamp,
        help=(
            "ISO-8601 upper bound on trace timestamps "
            "(inclusive). Default: no upper bound."
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


def _parse_iso_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{value!r} is not a valid ISO-8601 "
            f"timestamp. Pass a value such as "
            f"'2026-05-01T00:00:00Z'."
        ) from exc


def _print_success_block(
    *,
    manifest_path: Path,
    case_id: str,
    case_dir: Path,
    since: datetime | None,
    until: datetime | None,
    result: FetchedObservability,
) -> None:
    print(
        "\n".join(
            [
                "LangFuse observability fetch: COMPLETE",
                f"  manifest: {manifest_path}",
                f"  case_id: {case_id}",
                f"  case_dir: {case_dir}",
                f"  host: {result.host}",
                f"  session_id: {result.session_id}",
                f"  since: {_format_optional_timestamp(since)}",
                f"  until: {_format_optional_timestamp(until)}",
                f"  traces_matched: {len(result.trace_ids)}",
                f"  observations_fetched: {result.observation_count}",
                f"  tool_calls_written: {result.tool_call_count}",
                f"  routing_decisions_written: {result.routing_decision_count}",
                f"  step_count_total: {result.step_count_total}",
                f"  generations_written: {result.generation_count}",
                f"  generations_with_tokens: {_format_coverage(result.generations_with_tokens, result.generation_count)}",
                f"  generations_with_cost: {_format_coverage(result.generations_with_cost, result.generation_count)}",
                f"  generations_with_interval: {_format_coverage(result.generations_with_interval, result.generation_count)}",
                f"  total_tokens: {_format_optional_scalar(result.total_tokens)}",
                f"  total_cost_usd: {_format_optional_cost(result.total_cost_usd)}",
                f"  tool_calls_path: {result.written.tool_calls_path}",
                f"  routing_decisions_path: {result.written.routing_decisions_path}",
                f"  step_count_path: {result.written.step_count_path}",
                f"  generations_path: {result.written.generations_path}",
            ]
        )
    )


def _format_optional_scalar(value: int | None) -> str:
    return "unset" if value is None else str(value)


def _format_coverage(populated: int, total: int) -> str:
    if total == 0:
        return "0/0"
    return f"{populated}/{total}"


def _format_optional_cost(value: float | None) -> str:
    return "unset" if value is None else f"{value:.6f}"


def _format_optional_timestamp(
    value: datetime | None,
) -> str:
    return "unset" if value is None else value.isoformat()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    logger = configure_script_logging(
        script_name="fetch_observability",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(
        script_name="fetch_observability"
    )
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
                "add the case to the manifest's "
                "cases: list.\n"
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
                "manifest and case to capture the case "
                "directory before fetching upstream "
                "observability into it.",
                case_dir,
                extra={
                    "case_id": args.case,
                    "case_dir": str(case_dir),
                },
            )
            return 1

        if manifest.observability.langfuse is None:
            logger.error(
                "%s",
                LangfuseSourceNotDeclared(args.path),
                extra={"manifest_path": str(args.path)},
            )
            return 1

        session_id = (
            args.session_id
            if args.session_id is not None
            else case.id
        )

        try:
            with metrics.phase("fetch_observability"):
                result = fetch_langfuse_observability(
                    case_dir=case_dir,
                    source=manifest.observability.langfuse,
                    session_id=session_id,
                    since=args.since,
                    until=args.until,
                )
        except ObservabilityFetcherError as exc:
            logger.error(
                "%s",
                exc,
                extra={
                    "case_id": args.case,
                    "case_dir": str(case_dir),
                },
            )
            return 1

        _print_success_block(
            manifest_path=args.path,
            case_id=case.id,
            case_dir=case_dir,
            since=args.since,
            until=args.until,
            result=result,
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
