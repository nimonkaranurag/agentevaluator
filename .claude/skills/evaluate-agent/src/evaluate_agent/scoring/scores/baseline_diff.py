"""
Compute the per-assertion delta between two AgentScore records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from evaluate_agent.common.errors.scoring import (
    BaselineAgentMismatchError,
)
from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.schema import Slug
from evaluate_agent.scoring.outcomes import (
    AssertionKind,
    AssertionOutcome,
)
from evaluate_agent.scoring.scores.case_score import (
    CaseScore,
)
from pydantic import Field, model_validator

if TYPE_CHECKING:
    from evaluate_agent.scoring.scores.agent_score import (
        AgentScore,
    )

OutcomeStatus = Literal["passed", "failed", "inconclusive"]

AssertionTransition = Literal[
    "newly_passing",
    "newly_failing",
    "newly_inconclusive",
    "unchanged",
    "introduced",
    "removed",
]

_ASSERTION_TRANSITIONS: tuple[AssertionTransition, ...] = (
    "newly_passing",
    "newly_failing",
    "newly_inconclusive",
    "unchanged",
    "introduced",
    "removed",
)


class AssertionDiff(StrictFrozen):
    case_id: Annotated[
        Slug,
        Field(
            description=(
                "Case identifier the assertion was "
                "evaluated against in both runs (or the "
                "single run for introduced / removed "
                "transitions)."
            ),
        ),
    ]
    assertion_kind: Annotated[
        AssertionKind,
        Field(
            description=(
                "Schema-level kind of the assertion "
                "the diff entry pairs across runs."
            ),
        ),
    ]
    target: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Specific subject of the assertion "
                "(tool name for must_call / "
                "must_not_call; agent name for "
                "must_route_to). None for whole-case "
                "assertions. Pairs with assertion_kind "
                "and case_id to identify the assertion "
                "across runs."
            ),
        ),
    ]
    baseline_outcome: Annotated[
        OutcomeStatus | None,
        Field(
            default=None,
            description=(
                "Outcome status the assertion produced "
                "in the baseline run. None when the "
                "assertion did not appear in the "
                "baseline (transition=introduced)."
            ),
        ),
    ]
    current_outcome: Annotated[
        OutcomeStatus | None,
        Field(
            default=None,
            description=(
                "Outcome status the assertion produced "
                "in the current run. None when the "
                "assertion did not appear in the "
                "current run (transition=removed)."
            ),
        ),
    ]
    transition: Annotated[
        AssertionTransition,
        Field(
            description=(
                "Categorization of the change between "
                "baseline and current. newly_passing / "
                "newly_failing / newly_inconclusive "
                "describe transitions into the named "
                "status from a different prior status. "
                "unchanged means both runs produced the "
                "same status. introduced means the "
                "assertion was added since baseline. "
                "removed means the assertion was deleted "
                "since baseline."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _outcomes_match_transition(
        self,
    ) -> "AssertionDiff":
        if self.transition == "introduced":
            if (
                self.baseline_outcome is not None
                or self.current_outcome is None
            ):
                raise ValueError(
                    "introduced transitions require "
                    "baseline_outcome=None and "
                    "current_outcome set"
                )
            return self
        if self.transition == "removed":
            if (
                self.current_outcome is not None
                or self.baseline_outcome is None
            ):
                raise ValueError(
                    "removed transitions require "
                    "current_outcome=None and "
                    "baseline_outcome set"
                )
            return self
        if (
            self.baseline_outcome is None
            or self.current_outcome is None
        ):
            raise ValueError(
                f"transition={self.transition!r} "
                f"requires both baseline_outcome and "
                f"current_outcome to be set"
            )
        if self.transition == "unchanged":
            if (
                self.baseline_outcome
                != self.current_outcome
            ):
                raise ValueError(
                    "unchanged transitions require "
                    "baseline_outcome == "
                    "current_outcome"
                )
            return self
        expected_current: OutcomeStatus = (
            "passed"
            if self.transition == "newly_passing"
            else (
                "failed"
                if self.transition == "newly_failing"
                else "inconclusive"
            )
        )
        if self.current_outcome != expected_current:
            raise ValueError(
                f"transition={self.transition!r} "
                f"requires current_outcome="
                f"{expected_current!r}, got "
                f"{self.current_outcome!r}"
            )
        if self.baseline_outcome == expected_current:
            raise ValueError(
                f"transition={self.transition!r} "
                f"requires baseline_outcome to differ "
                f"from current_outcome"
            )
        return self


class BaselineDiffSummary(StrictFrozen):
    newly_passing: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Count of assertions that transitioned "
                "into the passed status."
            ),
        ),
    ]
    newly_failing: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Count of assertions that transitioned "
                "into the failed status."
            ),
        ),
    ]
    newly_inconclusive: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Count of assertions that transitioned "
                "into the inconclusive status."
            ),
        ),
    ]
    unchanged: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Count of assertions whose status was "
                "the same in baseline and current."
            ),
        ),
    ]
    introduced: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Count of assertions that appear in "
                "the current run but not in the "
                "baseline."
            ),
        ),
    ]
    removed: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Count of assertions that appear in "
                "the baseline but not in the current "
                "run."
            ),
        ),
    ]


class BaselineDiff(StrictFrozen):
    baseline_run_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "run_id of the AgentScore the diff "
                "treats as the prior reference point."
            ),
        ),
    ]
    baseline_agent_name: Annotated[
        Slug,
        Field(
            description=(
                "agent_name of the baseline AgentScore. "
                "Must match the current "
                "agent_name; compute_baseline_diff "
                "rejects mismatched agents."
            ),
        ),
    ]
    current_run_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "run_id of the AgentScore the diff "
                "compares against the baseline."
            ),
        ),
    ]
    current_agent_name: Annotated[
        Slug,
        Field(
            description=(
                "agent_name of the current AgentScore."
            ),
        ),
    ]
    summary: Annotated[
        BaselineDiffSummary,
        Field(
            description=(
                "Per-transition counts. Sums equal the "
                "lengths of the corresponding tuples."
            ),
        ),
    ]
    newly_passing: Annotated[
        tuple[AssertionDiff, ...],
        Field(
            description=(
                "Assertions that newly produce passed. "
                "Sorted by case_id, assertion_kind, "
                "target."
            ),
        ),
    ]
    newly_failing: Annotated[
        tuple[AssertionDiff, ...],
        Field(
            description=(
                "Assertions that newly produce failed. "
                "Sorted by case_id, assertion_kind, "
                "target."
            ),
        ),
    ]
    newly_inconclusive: Annotated[
        tuple[AssertionDiff, ...],
        Field(
            description=(
                "Assertions that newly produce "
                "inconclusive. Sorted by case_id, "
                "assertion_kind, target."
            ),
        ),
    ]
    unchanged: Annotated[
        tuple[AssertionDiff, ...],
        Field(
            description=(
                "Assertions whose status did not "
                "change. Sorted by case_id, "
                "assertion_kind, target."
            ),
        ),
    ]
    introduced: Annotated[
        tuple[AssertionDiff, ...],
        Field(
            description=(
                "Assertions present in current but "
                "absent in baseline. Sorted by "
                "case_id, assertion_kind, target."
            ),
        ),
    ]
    removed: Annotated[
        tuple[AssertionDiff, ...],
        Field(
            description=(
                "Assertions present in baseline but "
                "absent in current. Sorted by "
                "case_id, assertion_kind, target."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _summary_matches_buckets(
        self,
    ) -> "BaselineDiff":
        for transition in _ASSERTION_TRANSITIONS:
            bucket = getattr(self, transition)
            count = getattr(self.summary, transition)
            if len(bucket) != count:
                raise ValueError(
                    f"summary.{transition}={count} "
                    f"does not match bucket length "
                    f"{len(bucket)}"
                )
            for entry in bucket:
                if entry.transition != transition:
                    raise ValueError(
                        f"bucket {transition!r} "
                        f"contains entry with "
                        f"transition="
                        f"{entry.transition!r}"
                    )
        return self


def compute_baseline_diff(
    *,
    baseline: AgentScore,
    current: AgentScore,
) -> BaselineDiff:
    if baseline.agent_name != current.agent_name:
        raise BaselineAgentMismatchError(
            baseline_agent_name=baseline.agent_name,
            current_agent_name=current.agent_name,
        )
    baseline_index = _index_outcomes(baseline)
    current_index = _index_outcomes(current)
    keys = sorted(set(baseline_index) | set(current_index))
    buckets: dict[
        AssertionTransition, list[AssertionDiff]
    ] = {
        transition: []
        for transition in _ASSERTION_TRANSITIONS
    }
    for key in keys:
        case_id, assertion_kind, target = key
        baseline_outcome = baseline_index.get(key)
        current_outcome = current_index.get(key)
        transition = _classify_transition(
            baseline_outcome=baseline_outcome,
            current_outcome=current_outcome,
        )
        buckets[transition].append(
            AssertionDiff(
                case_id=case_id,
                assertion_kind=assertion_kind,
                target=target,
                baseline_outcome=baseline_outcome,
                current_outcome=current_outcome,
                transition=transition,
            )
        )
    summary = BaselineDiffSummary(
        newly_passing=len(buckets["newly_passing"]),
        newly_failing=len(buckets["newly_failing"]),
        newly_inconclusive=len(
            buckets["newly_inconclusive"]
        ),
        unchanged=len(buckets["unchanged"]),
        introduced=len(buckets["introduced"]),
        removed=len(buckets["removed"]),
    )
    return BaselineDiff(
        baseline_run_id=baseline.run_id,
        baseline_agent_name=baseline.agent_name,
        current_run_id=current.run_id,
        current_agent_name=current.agent_name,
        summary=summary,
        newly_passing=tuple(buckets["newly_passing"]),
        newly_failing=tuple(buckets["newly_failing"]),
        newly_inconclusive=tuple(
            buckets["newly_inconclusive"]
        ),
        unchanged=tuple(buckets["unchanged"]),
        introduced=tuple(buckets["introduced"]),
        removed=tuple(buckets["removed"]),
    )


def _index_outcomes(
    score: AgentScore,
) -> dict[
    tuple[Slug, AssertionKind, str | None],
    OutcomeStatus,
]:
    indexed: dict[
        tuple[Slug, AssertionKind, str | None],
        OutcomeStatus,
    ] = {}
    for case_score in score.case_scores:
        _index_case_outcomes(case_score, indexed)
    return indexed


def _index_case_outcomes(
    case_score: CaseScore,
    indexed: dict[
        tuple[Slug, AssertionKind, str | None],
        OutcomeStatus,
    ],
) -> None:
    for outcome in case_score.outcomes:
        key = (
            case_score.case_id,
            outcome.assertion_kind,
            outcome.target,
        )
        if key in indexed:
            raise ValueError(
                f"Duplicate assertion identity "
                f"{key!r} found in case_score "
                f"{case_score.case_id!r}; cannot "
                f"diff scores with non-unique "
                f"(case_id, assertion_kind, target) "
                f"tuples."
            )
        indexed[key] = _outcome_status(outcome)


def _outcome_status(
    outcome: AssertionOutcome,
) -> OutcomeStatus:
    return outcome.outcome


def _classify_transition(
    *,
    baseline_outcome: OutcomeStatus | None,
    current_outcome: OutcomeStatus | None,
) -> AssertionTransition:
    if (
        baseline_outcome is None
        and current_outcome is not None
    ):
        return "introduced"
    if (
        current_outcome is None
        and baseline_outcome is not None
    ):
        return "removed"
    if baseline_outcome == current_outcome:
        return "unchanged"
    if current_outcome == "passed":
        return "newly_passing"
    if current_outcome == "failed":
        return "newly_failing"
    return "newly_inconclusive"


__all__ = [
    "AssertionDiff",
    "AssertionTransition",
    "BaselineDiff",
    "BaselineDiffSummary",
    "OutcomeStatus",
    "compute_baseline_diff",
]
