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
Open a live web agent and capture artifacts for one declared case.

Captures a landing screenshot and DOM snapshot by default. With
--submit, also types case.input into the agent's primary input field
and captures a post-submit screenshot and DOM snapshot.

Exits 0 on success; 1 on any manifest, auth, interaction, or driver
error (printed to stderr).
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
    DOMSnapshotter,
    InputElementNotFound,
    MissingAuthEnvVar,
    RunArtifactLayout,
    open_session,
    submit_case_input,
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
        description=(
            "Open a live web agent in a sandboxed "
            "browser and capture artifacts for one "
            "declared case."
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
        help="Id of the case (under manifest.cases) to run.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help=(
            "After landing capture, type case.input into "
            "the agent's primary input field, press Enter, "
            "and capture a post-submit screenshot and "
            "DOM snapshot."
        ),
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
    dom_snapshotter = DOMSnapshotter(
        layout=layout, case_id=case.id
    )
    trace_paths = layout.trace_paths(case.id)

    try:
        async with open_session(
            manifest.access,
            layout=layout,
            case_id=case.id,
            headless=not args.headed,
        ) as session:
            landing = await capture.screenshot(
                session.page, "landing"
            )
            landing_dom = await dom_snapshotter.snapshot(
                session.page, "landing"
            )
            submission: dict[str, object] | None = None
            if args.submit:
                selector_used = await submit_case_input(
                    session.page,
                    case_input=case.input,
                    input_selector=manifest.interaction.input_selector,
                    response_wait_ms=manifest.interaction.response_wait_ms,
                )
                after_submit = await capture.screenshot(
                    session.page, "after_submit"
                )
                after_submit_dom = (
                    await dom_snapshotter.snapshot(
                        session.page, "after_submit"
                    )
                )
                submission = {
                    "selector_used": selector_used,
                    "response_wait_ms": manifest.interaction.response_wait_ms,
                    "screenshot": after_submit,
                    "dom_snapshot": after_submit_dom,
                }
    except (
        MissingAuthEnvVar,
        InputElementNotFound,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    title = (
        "Case submission complete."
        if submission is not None
        else "Landing capture complete."
    )
    lines = [
        f"OK: {title}",
        f"  agent:                    {manifest.name}",
        f"  case:                     {case.id}",
        f"  run_dir:                  {layout.run_dir}",
        f"  landing_screenshot:       {landing}",
        f"  landing_dom_snapshot:     {landing_dom}",
    ]
    if submission is not None:
        lines.extend(
            [
                f"  input_selector_used:      {submission['selector_used']}",
                f"  response_wait_ms:         {submission['response_wait_ms']}",
                f"  after_submit_screenshot:  {submission['screenshot']}",
                f"  after_submit_dom:         {submission['dom_snapshot']}",
            ]
        )
    lines.extend(
        [
            f"  trace_dir:                {trace_paths.trace_dir}",
            f"  trace_har:                {trace_paths.har_path}",
            f"  trace_requests:           {trace_paths.requests_path}",
            f"  trace_responses:          {trace_paths.responses_path}",
            f"  trace_console:            {trace_paths.console_path}",
            f"  trace_page_errors:        {trace_paths.page_errors_path}",
        ]
    )
    print("\n".join(lines))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    return asyncio.run(_drive(args))


if __name__ == "__main__":
    sys.exit(main())
