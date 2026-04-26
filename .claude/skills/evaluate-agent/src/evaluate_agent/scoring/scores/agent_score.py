"""
Compose per-case scores into a single agent-level evaluation record.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from evaluate_agent.artifact_layout import RUN_ID_FORMAT
from evaluate_agent.manifest.schema import Slug
from evaluate_agent.scoring.outcomes import AssertionKind
from evaluate_agent.scoring.scores.case_score import (
    CaseScore,
)
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

TargetedAssertionKind = Literal[
    "must_call",
    "must_not_call",
    "must_route_to",
]

ASSERTION_KIND_SCHEMA_ORDER: tuple[AssertionKind, ...] = (
    "final_response_contains",
    "must_call",
    "must_not_call",
    "must_route_to",
    "max_steps",
    "no_uncaught_page_errors",
)

_TARGETED_ASSERTION_KINDS: frozenset[AssertionKind] = (
    frozenset(
        ("must_call", "must_not_call", "must_route_to")
    )
)


def _validate_run_id_format(value: str) -> str:
    try:
        datetime.strptime(value, RUN_ID_FORMAT)
    except ValueError as exc:
        raise ValueError(
            f"run_id {value!r} is not formatted as "
            f"YYYYMMDDTHHMMSSZ (UTC, e.g. "
            f"20260425T173000Z)"
        ) from exc
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AssertionKindRollup(_Strict):
    assertion_kind: Annotated[
        AssertionKind,
        Field(
            description=(
                "Schema-level kind whose outcomes are "
                "aggregated in this rollup."
            ),
        ),
    ]
    total: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Number of outcomes for this kind across "
                "every case in the agent score."
            ),
        ),
    ]
    passed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes for this kind whose status is "
                "passed."
            ),
        ),
    ]
    failed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes for this kind whose status is "
                "failed."
            ),
        ),
    ]
    inconclusive: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes for this kind whose status is "
                "inconclusive."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _counts_partition_total(
        self,
    ) -> "AssertionKindRollup":
        if (
            self.passed + self.failed + self.inconclusive
            != self.total
        ):
            raise ValueError(
                f"counts do not partition total: "
                f"passed={self.passed} + "
                f"failed={self.failed} + "
                f"inconclusive={self.inconclusive} != "
                f"total={self.total}"
            )
        return self


class AssertionTargetRollup(_Strict):
    assertion_kind: Annotated[
        TargetedAssertionKind,
        Field(
            description=(
                "Per-target assertion kind whose outcomes "
                "are aggregated for this target. The "
                "non-targeted kinds "
                "(final_response_contains, max_steps) "
                "never appear in target rollups."
            ),
        ),
    ]
    target: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Tool name (must_call, must_not_call) or "
                "agent name (must_route_to) the rollup "
                "aggregates over."
            ),
        ),
    ]
    total: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Number of outcomes for this "
                "(assertion_kind, target) pair across "
                "every case in the agent score."
            ),
        ),
    ]
    passed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes for this pair whose status is "
                "passed."
            ),
        ),
    ]
    failed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes for this pair whose status is "
                "failed."
            ),
        ),
    ]
    inconclusive: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes for this pair whose status is "
                "inconclusive."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _counts_partition_total(
        self,
    ) -> "AssertionTargetRollup":
        if (
            self.passed + self.failed + self.inconclusive
            != self.total
        ):
            raise ValueError(
                f"counts do not partition total: "
                f"passed={self.passed} + "
                f"failed={self.failed} + "
                f"inconclusive={self.inconclusive} != "
                f"total={self.total}"
            )
        return self


class CaseOutcomeRollup(_Strict):
    total: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Number of cases the agent score "
                "aggregates."
            ),
        ),
    ]
    fully_passed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Cases whose every assertion outcome was "
                "passed (no failures, no inconclusives, "
                "at least one outcome). Mutually "
                "exclusive with with_no_assertions."
            ),
        ),
    ]
    with_any_failure: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Cases with at least one failed outcome. "
                "Overlaps with with_any_inconclusive when "
                "a case has both."
            ),
        ),
    ]
    with_any_inconclusive: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Cases with at least one inconclusive "
                "outcome. Overlaps with with_any_failure "
                "when a case has both."
            ),
        ),
    ]
    with_no_assertions: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Cases that declared zero assertions and "
                "therefore have zero outcomes. Mutually "
                "exclusive with fully_passed."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _categories_within_total(
        self,
    ) -> "CaseOutcomeRollup":
        for name, value in (
            ("fully_passed", self.fully_passed),
            ("with_any_failure", self.with_any_failure),
            (
                "with_any_inconclusive",
                self.with_any_inconclusive,
            ),
            (
                "with_no_assertions",
                self.with_no_assertions,
            ),
        ):
            if value > self.total:
                raise ValueError(
                    f"{name}={value} exceeds "
                    f"total={self.total}"
                )
        if (
            self.fully_passed + self.with_no_assertions
            > self.total
        ):
            raise ValueError(
                f"fully_passed and with_no_assertions are "
                f"mutually exclusive but their sum "
                f"({self.fully_passed} + "
                f"{self.with_no_assertions}) exceeds "
                f"total={self.total}"
            )
        return self


class AgentRollup(_Strict):
    total_assertions: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Sum of outcomes across every case in the "
                "agent score."
            ),
        ),
    ]
    passed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes whose status is passed across "
                "every case."
            ),
        ),
    ]
    failed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes whose status is failed across "
                "every case."
            ),
        ),
    ]
    inconclusive: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Outcomes whose status is inconclusive "
                "across every case."
            ),
        ),
    ]
    by_assertion_kind: Annotated[
        tuple[AssertionKindRollup, ...],
        Field(
            description=(
                "One rollup per assertion kind that had "
                "at least one outcome. Listed in the "
                "schema order final_response_contains, "
                "must_call, must_not_call, must_route_to, "
                "max_steps. Kinds with zero outcomes are "
                "omitted."
            ),
        ),
    ]
    by_target: Annotated[
        tuple[AssertionTargetRollup, ...],
        Field(
            description=(
                "One rollup per (assertion kind, target) "
                "pair for the per-target kinds "
                "(must_call, must_not_call, "
                "must_route_to). Sorted by assertion kind "
                "in schema order, then by target "
                "lexicographically. Empty when the agent "
                "declares no per-target assertions."
            ),
        ),
    ]
    cases: Annotated[
        CaseOutcomeRollup,
        Field(
            description=(
                "Case-granularity counts across the agent."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _counts_partition_total(self) -> "AgentRollup":
        if (
            self.passed + self.failed + self.inconclusive
            != self.total_assertions
        ):
            raise ValueError(
                f"counts do not partition "
                f"total_assertions: "
                f"passed={self.passed} + "
                f"failed={self.failed} + "
                f"inconclusive={self.inconclusive} != "
                f"total_assertions={self.total_assertions}"
            )
        return self

    @model_validator(mode="after")
    def _by_kind_totals_match_top_level(
        self,
    ) -> "AgentRollup":
        kind_total = sum(
            row.total for row in self.by_assertion_kind
        )
        if kind_total != self.total_assertions:
            raise ValueError(
                f"by_assertion_kind totals "
                f"({kind_total}) do not match "
                f"total_assertions "
                f"({self.total_assertions})"
            )
        return self

    @model_validator(mode="after")
    def _by_target_totals_match_targeted_kinds(
        self,
    ) -> "AgentRollup":
        kind_to_total: dict[str, int] = {
            row.assertion_kind: row.total
            for row in self.by_assertion_kind
            if row.assertion_kind
            in _TARGETED_ASSERTION_KINDS
        }
        target_totals: Counter[str] = Counter()
        for row in self.by_target:
            target_totals[row.assertion_kind] += row.total
        for kind, kind_total in kind_to_total.items():
            target_total = target_totals.get(kind, 0)
            if target_total != kind_total:
                raise ValueError(
                    f"by_target totals for "
                    f"{kind!r} ({target_total}) do not "
                    f"match by_assertion_kind total "
                    f"({kind_total})"
                )
        for kind in target_totals:
            if kind not in kind_to_total:
                raise ValueError(
                    f"by_target references "
                    f"assertion_kind {kind!r} but "
                    f"by_assertion_kind has no row for it"
                )
        return self


class AgentScore(_Strict):
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
        AfterValidator(_validate_run_id_format),
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


__all__ = [
    "ASSERTION_KIND_SCHEMA_ORDER",
    "AgentRollup",
    "AgentScore",
    "AssertionKindRollup",
    "AssertionTargetRollup",
    "CaseOutcomeRollup",
    "TargetedAssertionKind",
    "score_agent",
]
