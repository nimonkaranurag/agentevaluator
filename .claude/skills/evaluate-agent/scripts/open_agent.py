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

from evaluate_agent.artifact_layout import (  # noqa: E402
    InvalidRunId,
    RunArtifactLayout,
)
from evaluate_agent.capture_labels import (  # noqa: E402
    LANDING_LABEL,
    POST_SUBMIT_LABEL,
)
from evaluate_agent.driver import (  # noqa: E402
    NAVIGATED_EVENT_SUFFIX,
    PAGE_ERROR_EVENT_SUFFIX,
    DOMSnapshotter,
    InputElementNotFound,
    MissingAuthEnvVar,
    Screenshotter,
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
        "--run-id",
        default=None,
        help=(
            "Reuse a pre-committed run id "
            "(format YYYYMMDDTHHMMSSZ, UTC) so multiple "
            "invocations write artifacts under the same "
            "<runs-root>/<agent>/<run-id>/ directory. "
            "Required when this script is dispatched as "
            "part of a swarm so every sub-agent shares "
            "one run directory. Default: a fresh UTC "
            "timestamp captured at invocation time."
        ),
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window (default: headless).",
    )
    return parser.parse_args(argv)


def _list_event_artifacts(
    artifact_dir: Path,
    event_suffix: str,
    extension: str,
) -> list[Path]:
    if not artifact_dir.is_dir():
        return []
    return sorted(
        artifact_dir.glob(
            f"auto-*-{event_suffix}.{extension}"
        )
    )


def _render_event_section(
    label: str, artifacts: list[Path]
) -> list[str]:
    header = f"  {label + ':':<26}{len(artifacts)} captured"
    rows = [
        f"  {label}[{index}]: {path}"
        for index, path in enumerate(artifacts, start=1)
    ]
    return [header, *rows]


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

    try:
        layout = (
            RunArtifactLayout.from_run_id(
                agent_name=manifest.name,
                run_id=args.run_id,
                runs_root=args.runs_root,
            )
            if args.run_id is not None
            else RunArtifactLayout.for_agent(
                agent_name=manifest.name,
                runs_root=args.runs_root,
            )
        )
    except InvalidRunId as exc:
        print(str(exc), file=sys.stderr)
        return 1
    screenshotter = Screenshotter(
        layout=layout, case_id=case.id
    )
    dom_snapshotter = DOMSnapshotter(
        layout=layout, case_id=case.id
    )
    trace_paths = layout.trace_paths(case.id)
    auto_dom_dir = layout.dom_snapshot_dir(case.id)
    case_dir = layout.case_dir(case.id)

    try:
        async with open_session(
            manifest.access,
            layout=layout,
            case_id=case.id,
            headless=not args.headed,
        ) as session:
            landing = await screenshotter.screenshot(
                session.page, LANDING_LABEL
            )
            landing_dom = await dom_snapshotter.snapshot(
                session.page, LANDING_LABEL
            )
            submission: dict[str, object] | None = None
            if args.submit:
                selector_used = await submit_case_input(
                    session.page,
                    case_input=case.input,
                    input_selector=manifest.interaction.input_selector,
                    response_wait_ms=manifest.interaction.response_wait_ms,
                )
                after_submit = (
                    await screenshotter.screenshot(
                        session.page, POST_SUBMIT_LABEL
                    )
                )
                after_submit_dom = (
                    await dom_snapshotter.snapshot(
                        session.page, POST_SUBMIT_LABEL
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
    nav_dom_snapshots = _list_event_artifacts(
        auto_dom_dir, NAVIGATED_EVENT_SUFFIX, "html"
    )
    page_error_dom_snapshots = _list_event_artifacts(
        auto_dom_dir, PAGE_ERROR_EVENT_SUFFIX, "html"
    )
    nav_screenshots = _list_event_artifacts(
        case_dir, NAVIGATED_EVENT_SUFFIX, "png"
    )
    page_error_screenshots = _list_event_artifacts(
        case_dir, PAGE_ERROR_EVENT_SUFFIX, "png"
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
    lines.extend(
        _render_event_section(
            "nav_dom_snapshots", nav_dom_snapshots
        )
    )
    lines.extend(
        _render_event_section(
            "page_error_dom_snapshots",
            page_error_dom_snapshots,
        )
    )
    lines.extend(
        _render_event_section(
            "nav_screenshots", nav_screenshots
        )
    )
    lines.extend(
        _render_event_section(
            "page_error_screenshots",
            page_error_screenshots,
        )
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
