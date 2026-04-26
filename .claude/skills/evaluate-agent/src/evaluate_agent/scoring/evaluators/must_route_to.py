"""
Evaluate the must_route_to assertion against the captured routing-decision log.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionInconclusive,
    AssertionOutcome,
    AssertionPassed,
    ObservabilityLogMalformed,
    ObservabilitySourceMissing,
)
from evaluate_agent.scoring.resolvers.observability.routing_decision_log import (  # noqa: E501
    resolve_routing_decision_log,
    routing_decision_log_path,
)
from evaluate_agent.scoring.structured_log_parsing import (
    StructuredLogParseError,
)


def evaluate_must_route_to(
    target_agent: str,
    case_dir: Path,
) -> AssertionOutcome:
    try:
        log = resolve_routing_decision_log(case_dir)
    except StructuredLogParseError as exc:
        return AssertionInconclusive(
            assertion_kind="must_route_to",
            target=target_agent,
            reason=ObservabilityLogMalformed.from_error(
                exc
            ),
        )
    if log is None:
        return AssertionInconclusive(
            assertion_kind="must_route_to",
            target=target_agent,
            reason=ObservabilitySourceMissing(
                needed_evidence=("routing_decision_log"),
                expected_artifact_path=(
                    routing_decision_log_path(case_dir)
                ),
            ),
        )
    for line_number, entry in enumerate(
        log.entries, start=1
    ):
        if entry.target_agent == target_agent:
            return AssertionPassed(
                assertion_kind="must_route_to",
                target=target_agent,
                evidence=AssertionEvidence(
                    artifact_path=log.path,
                    detail=(
                        f"matched at line {line_number} "
                        f"(span_id={entry.span_id})"
                    ),
                ),
            )
    observed_targets = sorted(
        {entry.target_agent for entry in log.entries}
    )
    return AssertionFailed(
        assertion_kind="must_route_to",
        target=target_agent,
        expected=target_agent,
        observed=", ".join(observed_targets) or None,
        evidence=AssertionEvidence(
            artifact_path=log.path,
            detail=(
                f"target agent not found in "
                f"{len(log.entries)} logged routing "
                f"decision(s)"
            ),
        ),
    )


__all__ = ["evaluate_must_route_to"]
