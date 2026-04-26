"""
Typed errors raised by the report renderer.
"""

from __future__ import annotations

from evaluate_agent.report.common.citation_validator import (
    CitationValidationFailure,
)


class UnresolvedCitationError(Exception):
    def __init__(
        self,
        failures: tuple[CitationValidationFailure, ...],
    ) -> None:
        if not failures:
            raise ValueError(
                "UnresolvedCitationError requires at "
                "least one failure; an empty failure "
                "tuple indicates the score is valid "
                "and the renderer should not raise."
            )
        self.failures = failures
        super().__init__(self._format(failures))

    @staticmethod
    def _format(
        failures: tuple[CitationValidationFailure, ...],
    ) -> str:
        lines = [
            f"{len(failures)} citation(s) inside the "
            f"score record do not resolve on disk:",
        ]
        for index, failure in enumerate(failures, start=1):
            lines.append(
                f"  ({index}) "
                f"{failure.score_path}: "
                f"{failure.artifact_path} "
                f"(expected: {failure.expected_kind})"
            )
        lines.append(
            "To proceed:\n"
            "  (1) Confirm the score JSON was "
            "produced by score_case.py or "
            "score_agent.py against the same run "
            "directory the citations point at. The "
            "most common cause is moving or deleting "
            "the run directory between scoring and "
            "rendering.\n"
            "  (2) If the run directory was "
            "relocated, regenerate the score record "
            "against its current location and "
            "re-invoke render_report.py.\n"
            "  (3) If the run directory was deleted, "
            "re-run open_agent.py (single case) or "
            "the swarm plan's driver_invocation "
            "entries (whole agent) to regenerate the "
            "artifacts, then re-score and re-render."
        )
        return "\n".join(lines)


__all__ = ["UnresolvedCitationError"]
