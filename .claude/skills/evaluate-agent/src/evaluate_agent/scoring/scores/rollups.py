"""
Rollup data shapes that aggregate per-case scores along three deterministic axes.
"""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal

from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.scoring.outcomes import AssertionKind
from pydantic import Field, model_validator

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
)

TARGETED_ASSERTION_KINDS: frozenset[AssertionKind] = (
    frozenset(
        ("must_call", "must_not_call", "must_route_to")
    )
)


class AssertionKindRollup(StrictFrozen):
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


class AssertionTargetRollup(StrictFrozen):
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


class CaseOutcomeRollup(StrictFrozen):
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


class AgentRollup(StrictFrozen):
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
            in TARGETED_ASSERTION_KINDS
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


__all__ = [
    "ASSERTION_KIND_SCHEMA_ORDER",
    "AgentRollup",
    "AssertionKindRollup",
    "AssertionTargetRollup",
    "CaseOutcomeRollup",
    "TARGETED_ASSERTION_KINDS",
    "TargetedAssertionKind",
]
