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
plan references, scores each entry's case against its declared
assertions via score_case, and emits a JSON AgentScore record to
stdout. The AgentScore carries every per-case CaseScore plus a
deterministic rollup that aggregates outcomes by assertion kind, by
target, and at case granularity.

When --baseline PATH is supplied, the AgentScore output additionally
carries a baseline_diff field that pairs every current assertion
outcome against the baseline outcome by (case_id, assertion_kind,
target). The baseline must be a prior AgentScore JSON for the SAME
agent (matching agent_name); a mismatched agent_name is rejected with
an actionable error.

Diagnostic logging (errors, warnings) is emitted on stderr in either
text or JSON form, controlled by --log-format.

Exits 0 once aggregation completes (regardless of pass / fail /
inconclusive counts). Exits 1 on any plan, manifest, baseline,
case-id, or case-directory error (logged to stderr with the actionable
recovery procedure embedded in the message).

When --metrics PATH is supplied, the script writes a single JSON
document to PATH at completion that records per-phase wall-clock timing
(load_plan, load_manifest, [load_baseline], resolve_cases, score_cases,
aggregate, [compute_baseline_diff]), the script's exit status, and
contextual identifiers (manifest_path, run_id).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.common.errors.scoring import (  # noqa: E402
    BaselineAgentMismatchError,
)
from evaluate_agent.common.phase_metrics import (  # noqa: E402
    MetricsCollector,
)
from evaluate_agent.common.script_logging import (  # noqa: E402
    LOG_FORMATS,
    configure_script_logging,
)
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
    BaselineDiff,
    CaseScore,
    compute_baseline_diff,
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


class _BaselineLoadError(_ScoreAgentError):
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
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help=(
            "Path to a prior AgentScore JSON file. When "
            "set, the emitted AgentScore carries a "
            "baseline_diff field that pairs every "
            "current assertion outcome against the "
            "baseline outcome by (case_id, "
            "assertion_kind, target). The baseline must "
            "carry the same agent_name as the current "
            "run."
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


def _load_baseline_score(
    baseline_path: Path,
) -> AgentScore:
    if not baseline_path.is_file():
        raise _BaselineLoadError(
            f"Baseline AgentScore file does not exist "
            f"or is not a file: {baseline_path}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path matches the JSON "
            f"file score_agent.py emitted on a prior "
            f"run for the same agent.\n"
            f"  (2) Re-invoke without --baseline to "
            f"skip the diff, or correct the path and "
            f"re-invoke."
        )
    raw = baseline_path.read_text(encoding="utf-8")
    try:
        return AgentScore.model_validate_json(raw)
    except ValidationError as exc:
        raise _BaselineLoadError(
            f"Baseline file at {baseline_path} did "
            f"not validate against the AgentScore "
            f"schema.\n"
            f"Validation errors:\n{exc}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was produced by "
            f"an unmodified score_agent.py "
            f"invocation.\n"
            f"  (2) Re-run score_agent.py against the "
            f"baseline plan and overwrite the file, "
            f"then re-invoke score_agent.py "
            f"--baseline."
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
    logger = configure_script_logging(
        script_name="score_agent",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(script_name="score_agent")
    exit_code = 1
    try:
        try:
            with metrics.phase("load_plan"):
                plan = _load_plan(args.plan.resolve())
        except _ScoreAgentError as exc:
            logger.error("%s", exc)
            return 1
        metrics.set_context(
            run_id=plan.run_id,
            manifest_path=str(plan.manifest_path),
        )

        try:
            with metrics.phase("load_manifest"):
                manifest = load_manifest(plan.manifest_path)
        except ManifestError as exc:
            logger.error(
                "Manifest referenced by the swarm plan "
                "failed to load: %s\n%s",
                plan.manifest_path,
                exc,
                extra={
                    "manifest_path": str(
                        plan.manifest_path
                    ),
                    "run_id": plan.run_id,
                },
            )
            return 1

        baseline_score: AgentScore | None = None
        if args.baseline is not None:
            try:
                with metrics.phase("load_baseline"):
                    baseline_score = _load_baseline_score(
                        args.baseline.resolve()
                    )
            except _ScoreAgentError as exc:
                logger.error("%s", exc)
                return 1

        try:
            with metrics.phase("resolve_cases"):
                resolved = _resolve_cases_against_manifest(
                    plan, manifest
                )
                _validate_case_dirs_present(resolved)
        except _ScoreAgentError as exc:
            logger.error(
                "%s",
                exc,
                extra={"run_id": plan.run_id},
            )
            return 1

        with metrics.phase("score_cases"):
            case_scores: list[CaseScore] = [
                score_case(
                    case=case,
                    case_dir=directive.case_dir,
                    max_dom_bytes=manifest.interaction.max_dom_bytes,
                )
                for directive, case in resolved
            ]
        with metrics.phase("aggregate"):
            agent_score: AgentScore = score_agent(
                case_scores=tuple(case_scores),
                agent_name=plan.agent_name,
                run_id=plan.run_id,
                runs_root=plan.runs_root,
                manifest_path=plan.manifest_path,
            )
        if baseline_score is not None:
            try:
                with metrics.phase("compute_baseline_diff"):
                    diff = compute_baseline_diff(
                        baseline=baseline_score,
                        current=agent_score,
                    )
                    agent_score = agent_score.model_copy(
                        update={"baseline_diff": diff}
                    )
            except BaselineAgentMismatchError as exc:
                logger.error(
                    "%s",
                    exc,
                    extra={"run_id": plan.run_id},
                )
                return 1
        print(agent_score.model_dump_json(indent=2))
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
