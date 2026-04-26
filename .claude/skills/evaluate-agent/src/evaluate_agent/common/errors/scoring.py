"""
Typed errors raised by the scoring layer.
"""

from __future__ import annotations

from pathlib import Path


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


__all__ = ["ObservabilityLogMalformedError"]
