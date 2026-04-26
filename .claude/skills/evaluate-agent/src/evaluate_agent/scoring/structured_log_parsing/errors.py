"""
Typed error raised when a structured log file is present but unparseable.
"""

from __future__ import annotations

from pathlib import Path


class StructuredLogParseError(ValueError):
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
            f"Structured log {path} is present but "
            f"could not be parsed at {location}: "
            f"{parse_error}.\n"
            f"To proceed:\n"
            f"  (1) Open the file and confirm it is "
            f"valid JSON. JSONL inputs require one "
            f"JSON object per line; single-document "
            f"inputs require exactly one top-level "
            f"object.\n"
            f"  (2) Confirm every entry validates "
            f"against the pydantic model named in "
            f"the parse_error above. Required fields "
            f"and constraints are documented on the "
            f"matching schema module under "
            f"src/evaluate_agent/scoring/.\n"
            f"  (3) Correct the offending entry. If "
            f"the file was produced by an upstream "
            f"fetcher, fix the fetcher's output "
            f"mapping. If the file is hand-authored, "
            f"correct it directly. Re-score the case "
            f"once the file validates."
        )


__all__ = ["StructuredLogParseError"]
