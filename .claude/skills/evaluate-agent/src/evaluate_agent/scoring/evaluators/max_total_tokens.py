"""
Evaluate the max_total_tokens assertion against the captured generation log.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    ObservabilitySourceMissing,
)
from evaluate_agent.scoring.resolvers.log_resolvers.generation_log import (  # noqa: E501
    generation_log_path,
    resolve_generation_log,
)

from .utils import resolve_observability_log


def evaluate_max_total_tokens(
    token_limit: int,
    case_dir: Path,
) -> AssertionOutcome:
    log = resolve_observability_log(
        case_dir=case_dir,
        assertion_kind="max_total_tokens",
        target=None,
        needed_evidence="generation_log",
        resolve=resolve_generation_log,
        log_path=generation_log_path,
    )
    if isinstance(log, AssertionInconclusive):
        return log
    contributions = [
        entry.total_tokens
        for entry in log.entries
        if entry.total_tokens is not None
    ]
    if not contributions:
        return AssertionInconclusive(
            assertion_kind="max_total_tokens",
            target=None,
            reason=ObservabilitySourceMissing(
                needed_evidence="generation_log",
                expected_artifact_path=log.path,
            ),
        )
    observed = sum(contributions)
    if observed <= token_limit:
        return AssertionPassed(
            assertion_kind="max_total_tokens",
            evidence=AssertionEvidence(
                artifact_path=log.path,
                detail=(
                    f"observed {observed} total token(s) "
                    f"across {len(contributions)} "
                    f"generation(s) within limit of "
                    f"{token_limit}"
                ),
            ),
        )
    return AssertionFailed(
        assertion_kind="max_total_tokens",
        expected=f"<= {token_limit}",
        observed=str(observed),
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"observed {observed} total token(s) "
                f"across {len(contributions)} "
                f"generation(s) exceeding limit of "
                f"{token_limit}"
            ),
        ),
    )


__all__ = ["evaluate_max_total_tokens"]
