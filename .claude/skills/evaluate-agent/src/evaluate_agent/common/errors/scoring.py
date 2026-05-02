"""
Typed errors raised by the scoring layer.
"""

from __future__ import annotations

from pathlib import Path


class BaselineAgentMismatchError(ValueError):
    def __init__(
        self,
        *,
        baseline_agent_name: str,
        current_agent_name: str,
    ) -> None:
        self.baseline_agent_name = baseline_agent_name
        self.current_agent_name = current_agent_name
        super().__init__(
            f"Cannot diff scores from different "
            f"agents: baseline.agent_name="
            f"{baseline_agent_name!r}, "
            f"current.agent_name="
            f"{current_agent_name!r}.\n"
            f"To proceed:\n"
            f"  (1) Confirm the baseline file is the "
            f"prior AgentScore for the same agent the "
            f"current run scored. The baseline path "
            f"should point at a JSON file that "
            f"score_agent.py emitted for "
            f"{current_agent_name!r}.\n"
            f"  (2) Re-invoke with --baseline pointing "
            f"at the prior AgentScore for "
            f"{current_agent_name!r}, or omit "
            f"--baseline to skip the diff."
        )


class ObservabilityLogMalformedError(ValueError):
    def __init__(
        self,
        path: Path,
        line_number: int | None,
        parse_error: str,
    ) -> None:
        self.path = path
        self.line_number = line_number
        self.parse_error = parse_error
        location = (
            f"line {line_number}"
            if line_number is not None
            else "the file body"
        )
        super().__init__(
            f"Observability log {path} is present but "
            f"could not be parsed at {location}: "
            f"{parse_error}.\n"
            f"To proceed:\n"
            f"  (1) Open the file and confirm it is "
            f"valid JSONL (one JSON object per line) "
            f"for tool_calls.jsonl and "
            f"routing_decisions.jsonl, or a single "
            f"JSON object for step_count.json.\n"
            f"  (2) Confirm every entry validates "
            f"against the on-disk schema documented in "
            f"src/evaluate_agent/scoring/observability/"
            f"schema.py — required "
            f"fields are tool_name + span_id "
            f"(tool_calls), target_agent + span_id "
            f"(routing_decisions), total_steps + "
            f"step_span_ids of matching length "
            f"(step_count).\n"
            f"  (3) If the file was produced by an "
            f"upstream fetcher, fix the fetcher's "
            f"output mapping. If the file is "
            f"hand-authored, correct the offending "
            f"entry. Re-score the case once the file "
            f"validates."
        )


__all__ = [
    "BaselineAgentMismatchError",
    "ObservabilityLogMalformedError",
]
