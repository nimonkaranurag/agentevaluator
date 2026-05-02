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

Exits 0 once the fetch completes (regardless of trace or observation
count). Exits 1 on any manifest, case-selection, case-directory,
credential, or LangFuse query error printed to stderr.
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
                f"  generations_with_latency: {_format_coverage(result.generations_with_latency, result.generation_count)}",
                f"  total_tokens: {_format_optional_scalar(result.total_tokens)}",
                f"  total_cost_usd: {_format_optional_cost(result.total_cost_usd)}",
                f"  total_latency_ms: {_format_optional_scalar(result.total_latency_ms)}",
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
            f"and case to capture the case directory "
            f"before fetching upstream observability "
            f"into it.",
            file=sys.stderr,
        )
        return 1

    if manifest.observability.langfuse is None:
        print(
            str(LangfuseSourceNotDeclared(args.path)),
            file=sys.stderr,
        )
        return 1

    session_id = (
        args.session_id
        if args.session_id is not None
        else case.id
    )

    try:
        result = fetch_langfuse_observability(
            case_dir=case_dir,
            source=manifest.observability.langfuse,
            session_id=session_id,
            since=args.since,
            until=args.until,
        )
    except ObservabilityFetcherError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print_success_block(
        manifest_path=args.path,
        case_id=case.id,
        case_dir=case_dir,
        since=args.since,
        until=args.until,
        result=result,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
