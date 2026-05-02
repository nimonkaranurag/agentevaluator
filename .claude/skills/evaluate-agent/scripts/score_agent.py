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
Score every captured case in a swarm plan into one agent-level record.

Reads a plan_swarm-produced JSON file from disk, loads the manifest the
plan references, scores each entry's case against its declared assertions
via score_case, and emits a JSON AgentScore record to stdout. The
AgentScore carries every per-case CaseScore plus a deterministic rollup
that aggregates outcomes by assertion kind, by target, and at case
granularity.

Exits 0 once aggregation completes (regardless of pass / fail /
inconclusive counts). Exits 1 on any plan, manifest, case-id, or
case-directory error printed to stderr.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.manifest import (  # noqa: E402
    AgentManifest,
    ManifestError,
    load_manifest,
)
from evaluate_agent.manifest.schema import (  # noqa: E402
    Case,
)
from evaluate_agent.orchestration import (  # noqa: E402
    CaseDirective,
    SwarmPlan,
)
from evaluate_agent.scoring import (  # noqa: E402
    AgentScore,
    CaseScore,
    score_agent,
    score_case,
)


class _ScoreAgentError(Exception):
    """
    Base for actionable failures the script reports to stderr.
    """


class _PlanLoadError(_ScoreAgentError):
    pass


class _PlanCaseMismatchError(_ScoreAgentError):
    pass


class _CaseDirMissingError(_ScoreAgentError):
    pass


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="score_agent",
        description=(
            "Score every captured case in a swarm plan "
            "and emit a single JSON AgentScore record "
            "to stdout."
        ),
    )
    parser.add_argument(
        "plan",
        type=Path,
        help=(
            "Path to the JSON swarm plan produced by "
            "plan_swarm.py. The plan names the manifest "
            "and every case directory the score "
            "aggregates."
        ),
    )
    return parser.parse_args(argv)


def _load_plan(plan_path: Path) -> SwarmPlan:
    if not plan_path.is_file():
        raise _PlanLoadError(
            f"Swarm plan file does not exist or is not "
            f"a file: {plan_path}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path matches the JSON "
            f"file written by plan_swarm.py.\n"
            f"  (2) If the plan was never generated, "
            f"run plan_swarm.py against the agent "
            f"manifest and pipe its stdout to a file, "
            f"then re-invoke score_agent.py with that "
            f"file path."
        )
    raw = plan_path.read_text(encoding="utf-8")
    try:
        return SwarmPlan.model_validate_json(raw)
    except ValidationError as exc:
        raise _PlanLoadError(
            f"Swarm plan at {plan_path} did not parse "
            f"as a valid SwarmPlan record.\n"
            f"Validation errors:\n{exc}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was produced by an "
            f"unmodified plan_swarm.py invocation.\n"
            f"  (2) Re-run plan_swarm.py against the "
            f"agent manifest and overwrite the file, "
            f"then re-invoke score_agent.py."
        ) from exc


def _resolve_cases_against_manifest(
    plan: SwarmPlan,
    manifest: AgentManifest,
) -> list[tuple[CaseDirective, Case]]:
    cases_by_id = {c.id: c for c in manifest.cases}
    missing: list[str] = []
    resolved: list[tuple[CaseDirective, Case]] = []
    for directive in plan.directives:
        case = cases_by_id.get(directive.case_id)
        if case is None:
            missing.append(directive.case_id)
            continue
        resolved.append((directive, case))
    if missing:
        declared = ", ".join(c.id for c in manifest.cases)
        raise _PlanCaseMismatchError(
            f"Swarm plan references case ids that the "
            f"manifest does not declare: "
            f"{', '.join(missing)}\n"
            f"Manifest declares: {declared}\n"
            f"To proceed:\n"
            f"  (1) Confirm the plan was generated from "
            f"the same manifest version. The plan's "
            f"manifest_path field points at "
            f"{plan.manifest_path}.\n"
            f"  (2) Regenerate the plan via "
            f"plan_swarm.py against the current "
            f"manifest and re-invoke score_agent.py."
        )
    return resolved


def _validate_case_dirs_present(
    resolved: list[tuple[CaseDirective, Case]],
) -> None:
    missing: list[Path] = [
        directive.case_dir
        for directive, _ in resolved
        if not directive.case_dir.is_dir()
    ]
    if missing:
        listing = "\n".join(f"  - {p}" for p in missing)
        raise _CaseDirMissingError(
            f"One or more case directories named in "
            f"the swarm plan do not exist or are not "
            f"directories:\n{listing}\n"
            f"To proceed:\n"
            f"  (1) Confirm every case in the plan was "
            f"driven to completion. The orchestrator "
            f"dispatches one sub-agent per directive; "
            f"each sub-agent uses its Playwright MCP "
            f"browser to navigate, run preconditions, "
            f"submit case_input, and write the "
            f"landing+after_submit screenshots and DOM "
            f"snapshots to the directive's declared "
            f"paths.\n"
            f"  (2) Re-dispatch sub-agents for the "
            f"missing directives. Every directive in "
            f"this plan shares the same run_id so "
            f"artifacts land in one run directory.\n"
            f"  (3) Once every case directory exists, "
            f"re-invoke score_agent.py with the same "
            f"plan path."
        )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    try:
        plan = _load_plan(args.plan.resolve())
    except _ScoreAgentError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        manifest = load_manifest(plan.manifest_path)
    except ManifestError as exc:
        print(
            f"Manifest referenced by the swarm plan "
            f"failed to load: {plan.manifest_path}\n"
            f"{exc}",
            file=sys.stderr,
        )
        return 1

    try:
        resolved = _resolve_cases_against_manifest(
            plan, manifest
        )
        _validate_case_dirs_present(resolved)
    except _ScoreAgentError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    case_scores: list[CaseScore] = [
        score_case(case=case, case_dir=directive.case_dir)
        for directive, case in resolved
    ]
    agent_score: AgentScore = score_agent(
        case_scores=tuple(case_scores),
        agent_name=plan.agent_name,
        run_id=plan.run_id,
        runs_root=plan.runs_root,
        manifest_path=plan.manifest_path,
    )
    print(agent_score.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
