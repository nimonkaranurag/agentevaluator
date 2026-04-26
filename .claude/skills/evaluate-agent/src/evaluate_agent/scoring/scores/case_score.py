"""
Compose per-assertion outcomes for one case into a single score record.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from evaluate_agent.manifest.schema import Case, Slug
from evaluate_agent.scoring.evaluators import (
    evaluate_final_response_contains,
    evaluate_max_steps,
    evaluate_must_call,
    evaluate_must_not_call,
    evaluate_must_route_to,
)
from evaluate_agent.scoring.outcomes import (
    AssertionOutcome,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaseScore(_Strict):
    case_id: Annotated[
        Slug,
        Field(
            description=(
                "Case identifier copied from the manifest "
                "the score originates from."
            ),
        ),
    ]
    case_dir: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the directory under "
                "which the case's screenshots, DOM "
                "snapshots, and trace artifacts live. "
                "Every passed or failed outcome cites a "
                "file under this path."
            ),
        ),
    ]
    outcomes: Annotated[
        tuple[AssertionOutcome, ...],
        Field(
            description=(
                "One outcome per declared assertion, in "
                "schema order: final_response_contains, "
                "then must_call (per tool), then "
                "must_not_call (per tool), then "
                "must_route_to, then max_steps. Empty "
                "when the case declares no assertions."
            ),
        ),
    ]

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(
            1
            for outcome in self.outcomes
            if outcome.outcome == "passed"
        )

    @property
    def failed(self) -> int:
        return sum(
            1
            for outcome in self.outcomes
            if outcome.outcome == "failed"
        )

    @property
    def inconclusive(self) -> int:
        return sum(
            1
            for outcome in self.outcomes
            if outcome.outcome == "inconclusive"
        )


def score_case(
    case: Case,
    case_dir: Path,
) -> CaseScore:
    outcomes: list[AssertionOutcome] = []
    assertions = case.assertions

    if assertions.final_response_contains is not None:
        outcomes.append(
            evaluate_final_response_contains(
                expected_substring=(
                    assertions.final_response_contains
                ),
                case_dir=case_dir,
            )
        )

    for tool in assertions.must_call:
        outcomes.append(
            evaluate_must_call(tool, case_dir=case_dir)
        )

    for tool in assertions.must_not_call:
        outcomes.append(
            evaluate_must_not_call(tool, case_dir=case_dir)
        )

    if assertions.must_route_to is not None:
        outcomes.append(
            evaluate_must_route_to(
                assertions.must_route_to,
                case_dir=case_dir,
            )
        )

    if assertions.max_steps is not None:
        outcomes.append(
            evaluate_max_steps(
                assertions.max_steps,
                case_dir=case_dir,
            )
        )

    return CaseScore(
        case_id=case.id,
        case_dir=case_dir,
        outcomes=tuple(outcomes),
    )


__all__ = ["CaseScore", "score_case"]
