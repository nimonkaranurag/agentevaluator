#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4>=4.12",
#     "pydantic>=2.7",
#     "pyyaml>=6",
# ]
# ///
"""
Render a CaseScore or AgentScore JSON record as Markdown.

Reads a score JSON file produced by score_case.py or score_agent.py,
verifies that every citation inside the record resolves to a real
artifact on disk, and emits a Markdown narrative to stdout. The
narrative cites the same evidence paths the score record carries, so a
reader can open each cited file and inspect the raw evidence.

Autodetects whether the input is an AgentScore (presence of the
agent_name field) or a CaseScore. Exits 0 once rendering completes.
Exits 1 on a missing or malformed score file, on a record that does
not validate as either type, or on any unresolved citation reported by
the renderer's structural integrity check.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from evaluate_agent.report import (  # noqa: E402
    UnresolvedCitationError,
    render_agent_score_markdown,
    render_case_score_markdown,
)
from evaluate_agent.scoring import (  # noqa: E402
    AgentScore,
    CaseScore,
)


class _RenderReportError(Exception):
    """
    Base for actionable failures the script reports to stderr.
    """


class _ScoreLoadError(_RenderReportError):
    pass


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="render_report",
        description=(
            "Render a CaseScore or AgentScore JSON "
            "record as a citation-grounded Markdown "
            "narrative on stdout."
        ),
    )
    parser.add_argument(
        "score",
        type=Path,
        help=(
            "Path to the JSON file produced by "
            "score_case.py (CaseScore) or "
            "score_agent.py (AgentScore). The script "
            "autodetects the record type."
        ),
    )
    return parser.parse_args(argv)


def _load_score(
    score_path: Path,
) -> CaseScore | AgentScore:
    if not score_path.is_file():
        raise _ScoreLoadError(
            f"Score file does not exist or is not a "
            f"file: {score_path}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path matches the "
            f"file the score command wrote (the JSON "
            f"emitted on stdout by score_case.py or "
            f"score_agent.py).\n"
            f"  (2) If the score was never persisted, "
            f"re-run the score command and pipe its "
            f"stdout to a file, then re-invoke "
            f"render_report.py with that file path."
        )
    raw = score_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _ScoreLoadError(
            f"Score file at {score_path} is not "
            f"valid JSON.\n"
            f"Parser detail: {exc}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was written "
            f"verbatim from the score command's "
            f"stdout (no truncation, no shell "
            f"interpolation).\n"
            f"  (2) Re-run the score command and "
            f"overwrite the file, then re-invoke "
            f"render_report.py."
        ) from exc

    if not isinstance(data, dict):
        raise _ScoreLoadError(
            f"Score file at {score_path} parsed as "
            f"{type(data).__name__}, not a JSON "
            f"object. CaseScore and AgentScore "
            f"records are JSON objects.\n"
            f"To proceed: confirm the file was "
            f"written verbatim from score_case.py "
            f"or score_agent.py and re-invoke "
            f"render_report.py."
        )

    if "agent_name" in data:
        return _validate_as(AgentScore, data, score_path)
    return _validate_as(CaseScore, data, score_path)


def _validate_as(
    model: type[CaseScore] | type[AgentScore],
    data: dict,
    score_path: Path,
) -> CaseScore | AgentScore:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise _ScoreLoadError(
            f"Score file at {score_path} did not "
            f"validate against the "
            f"{model.__name__} schema.\n"
            f"Validation errors:\n{exc}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was produced "
            f"by an unmodified score command "
            f"({'score_agent.py' if model is AgentScore else 'score_case.py'}).\n"
            f"  (2) Re-run that command against the "
            f"same inputs and overwrite the file, "
            f"then re-invoke render_report.py."
        ) from exc


def _render(
    score: CaseScore | AgentScore,
) -> str:
    if isinstance(score, AgentScore):
        return render_agent_score_markdown(score)
    return render_case_score_markdown(score)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    try:
        score = _load_score(args.score.resolve())
    except _RenderReportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        markdown = _render(score)
    except UnresolvedCitationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
