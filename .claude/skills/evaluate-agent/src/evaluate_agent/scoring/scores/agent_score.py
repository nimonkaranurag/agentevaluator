"""
Compose per-case scores into a single agent-level evaluation record.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from evaluate_agent.artifact_layout import parse_run_id
from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.schema import Slug
from evaluate_agent.scoring.outcomes import AssertionKind
from evaluate_agent.scoring.scores.case_score import (
    CaseScore,
)
from evaluate_agent.scoring.scores.rollups import (
    ASSERTION_KIND_SCHEMA_ORDER,
    AgentRollup,
    AssertionKindRollup,
    AssertionTargetRollup,
    CaseOutcomeRollup,
)
from pydantic import (
    AfterValidator,
    Field,
    model_validator,
)


def _run_id_validator(value: str) -> str:
    parse_run_id(value)
    return value


class AgentScore(StrictFrozen):
    agent_name: Annotated[
        Slug,
        Field(
            description=(
                "Agent identifier copied from "
                "manifest.name. Mirrors the run "
                "directory's first path segment under "
                "runs_root."
            ),
        ),
    ]
    run_id: Annotated[
        str,
        AfterValidator(_run_id_validator),
        Field(
            description=(
                "Shared run timestamp the case scores "
                "were captured under. Format: "
                "YYYYMMDDTHHMMSSZ (UTC). Mirrors the run "
                "directory name produced by "
                "RunArtifactLayout."
            ),
        ),
    ]
    runs_root: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the directory under "
                "which <agent_name>/<run_id>/ lives. "
                "Every case_score.case_dir starts with "
                "this path."
            ),
        ),
    ]
    manifest_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the agent.yaml manifest "
                "the case scores were derived from."
            ),
        ),
    ]
    case_scores: Annotated[
        tuple[CaseScore, ...],
        Field(
            min_length=1,
            description=(
                "Per-case scores in the order the cases "
                "were declared in the manifest. Every "
                "passed or failed assertion outcome "
                "inside a case score cites a real "
                "artifact under that case's case_dir."
            ),
        ),
    ]
    rollup: Annotated[
        AgentRollup,
        Field(
            description=(
                "Cross-case aggregation of the per-case "
                "scores. Computed deterministically from "
                "case_scores at composition time."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _case_ids_unique(self) -> "AgentScore":
        seen: set[str] = set()
        dups: set[str] = set()
        for cs in self.case_scores:
            if cs.case_id in seen:
                dups.add(cs.case_id)
            seen.add(cs.case_id)
        if dups:
            raise ValueError(
                f"case_scores contains duplicate case "
                f"ids: {sorted(dups)}"
            )
        return self


def score_agent(
    *,
    case_scores: tuple[CaseScore, ...],
    agent_name: Slug,
    run_id: str,
    runs_root: Path,
    manifest_path: Path,
) -> AgentScore:
    rollup = _compose_rollup(case_scores)
    return AgentScore(
        agent_name=agent_name,
        run_id=run_id,
        runs_root=runs_root,
        manifest_path=manifest_path,
        case_scores=case_scores,
        rollup=rollup,
    )


def _compose_rollup(
    case_scores: Iterable[CaseScore],
) -> AgentRollup:
    by_kind_total: Counter[AssertionKind] = Counter()
    by_kind_passed: Counter[AssertionKind] = Counter()
    by_kind_failed: Counter[AssertionKind] = Counter()
    by_kind_inconclusive: Counter[AssertionKind] = Counter()
    by_target_total: Counter[tuple[AssertionKind, str]] = (
        Counter()
    )
    by_target_passed: Counter[tuple[AssertionKind, str]] = (
        Counter()
    )
    by_target_failed: Counter[tuple[AssertionKind, str]] = (
        Counter()
    )
    by_target_inconclusive: Counter[
        tuple[AssertionKind, str]
    ] = Counter()

    case_total = 0
    cases_fully_passed = 0
    cases_with_any_failure = 0
    cases_with_any_inconclusive = 0
    cases_with_no_assertions = 0

    for cs in case_scores:
        case_total += 1
        case_passed = 0
        case_failed = 0
        case_inconclusive = 0
        for outcome in cs.outcomes:
            kind = outcome.assertion_kind
            by_kind_total[kind] += 1
            if outcome.outcome == "passed":
                by_kind_passed[kind] += 1
                case_passed += 1
            elif outcome.outcome == "failed":
                by_kind_failed[kind] += 1
                case_failed += 1
            else:
                by_kind_inconclusive[kind] += 1
                case_inconclusive += 1
            target = outcome.target
            if target is not None:
                key = (kind, target)
                by_target_total[key] += 1
                if outcome.outcome == "passed":
                    by_target_passed[key] += 1
                elif outcome.outcome == "failed":
                    by_target_failed[key] += 1
                else:
                    by_target_inconclusive[key] += 1
        outcome_total = (
            case_passed + case_failed + case_inconclusive
        )
        if outcome_total == 0:
            cases_with_no_assertions += 1
        elif case_failed == 0 and case_inconclusive == 0:
            cases_fully_passed += 1
        if case_failed > 0:
            cases_with_any_failure += 1
        if case_inconclusive > 0:
            cases_with_any_inconclusive += 1

    by_assertion_kind = tuple(
        AssertionKindRollup(
            assertion_kind=kind,
            total=by_kind_total[kind],
            passed=by_kind_passed[kind],
            failed=by_kind_failed[kind],
            inconclusive=by_kind_inconclusive[kind],
        )
        for kind in ASSERTION_KIND_SCHEMA_ORDER
        if by_kind_total[kind] > 0
    )
    sorted_target_keys = sorted(
        by_target_total.keys(),
        key=lambda k: (
            ASSERTION_KIND_SCHEMA_ORDER.index(k[0]),
            k[1],
        ),
    )
    by_target = tuple(
        AssertionTargetRollup(
            assertion_kind=kind,
            target=target,
            total=by_target_total[(kind, target)],
            passed=by_target_passed[(kind, target)],
            failed=by_target_failed[(kind, target)],
            inconclusive=by_target_inconclusive[
                (kind, target)
            ],
        )
        for kind, target in sorted_target_keys
    )
    return AgentRollup(
        total_assertions=sum(by_kind_total.values()),
        passed=sum(by_kind_passed.values()),
        failed=sum(by_kind_failed.values()),
        inconclusive=sum(by_kind_inconclusive.values()),
        by_assertion_kind=by_assertion_kind,
        by_target=by_target,
        cases=CaseOutcomeRollup(
            total=case_total,
            fully_passed=cases_fully_passed,
            with_any_failure=cases_with_any_failure,
            with_any_inconclusive=(
                cases_with_any_inconclusive
            ),
            with_no_assertions=cases_with_no_assertions,
        ),
    )


__all__ = ["AgentScore", "score_agent"]
