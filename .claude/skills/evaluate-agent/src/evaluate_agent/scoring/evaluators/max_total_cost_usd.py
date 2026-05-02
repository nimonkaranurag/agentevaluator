"""
Evaluate the max_total_cost_usd assertion against the captured generation log.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
)
from evaluate_agent.scoring.resolvers.log_resolvers.generation_log import (  # noqa: E501
    generation_log_path,
    resolve_generation_log,
)

from .utils import (
    gate_generation_field_coverage,
    resolve_observability_log,
)


def evaluate_max_total_cost_usd(
    cost_limit_usd: float,
    case_dir: Path,
) -> AssertionOutcome:
    log = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="max_total_cost_usd",
        target=None,
        needed_evidence="generation_log",
        resolve=resolve_generation_log,
        log_path=generation_log_path,
    )
    if isinstance(log, AssertionInconclusive):
        return log
    # Coverage gate before sum: a self-hosted LangFuse without
    # cost mapping leaves total_cost_usd null on every row.
    # Summing the populated subset would silently report a
    # cost below the cap and pass an assertion that should have
    # surfaced its missing-evidence shape to the operator.
    contributions = gate_generation_field_coverage(
        log=log,
        field_name="total_cost_usd",
        assertion_kind="max_total_cost_usd",
    )
    if isinstance(contributions, AssertionInconclusive):
        return contributions
    observed = sum(contributions)
    if observed <= cost_limit_usd:
        return AssertionPassed(
            assertion_kind="max_total_cost_usd",
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    f"observed ${observed:.6f} total cost "
                    f"across {len(contributions)} "
                    f"generation(s) within limit of "
                    f"${cost_limit_usd:.6f}"
                ),
            ),
        )
    return AssertionFailed(
        assertion_kind="max_total_cost_usd",
        expected=f"<= {cost_limit_usd:.6f}",
        observed=f"{observed:.6f}",
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"observed ${observed:.6f} total cost "
                f"across {len(contributions)} "
                f"generation(s) exceeding limit of "
                f"${cost_limit_usd:.6f}"
            ),
        ),
    )


__all__ = ["evaluate_max_total_cost_usd"]
