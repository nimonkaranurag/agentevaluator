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

Optionally embeds analytical narratives. Use --narrative <path> with a
CaseScore record to embed one analytical narrative under the case
section. Use --narratives-dir <dir> with an AgentScore record to embed
per-case narratives looked up by case_id; missing per-case files are
skipped silently and the report renders without their analytical
sections.

Autodetects whether the input is an AgentScore (presence of the
agent_name field) or a CaseScore. Exits 0 once rendering completes.
Exits 1 on a missing or malformed score file, on a record that does
not validate as either type, on an unresolved citation reported by
either structural integrity check, or on any narrative-grounding
violation.
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

from evaluate_agent.case_narrative import (  # noqa: E402
    CaseNarrative,
    load_case_narrative,
)
from evaluate_agent.common.errors.case_narrative import (  # noqa: E402
    CaseNarrativeError,
)
from evaluate_agent.report import (  # noqa: E402
    UnresolvedCitationError,
    render_agent_score_markdown,
    render_case_score_markdown,
)
from evaluate_agent.scoring import (  # noqa: E402
    AgentScore,
    CaseScore,
)

_NARRATIVE_FILE_SUFFIX = ".json"


class _RenderReportError(Exception):
    """
    Base for actionable failures the script reports to stderr.
    """


class _ScoreLoadError(_RenderReportError):
    pass


class _NarrativeFlagMisuseError(_RenderReportError):
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
    narrative_group = parser.add_mutually_exclusive_group()
    narrative_group.add_argument(
        "--narrative",
        type=Path,
        help=(
            "Path to a single CaseNarrative JSON file. "
            "Embeds the narrative under the case "
            "section. Only valid with a CaseScore "
            "record."
        ),
    )
    narrative_group.add_argument(
        "--narratives-dir",
        type=Path,
        help=(
            "Path to a directory containing "
            "<case_id>.json narrative files, one per "
            "case the agent score covers. Files for "
            "case ids the score does not declare are "
            "rejected; case ids without a "
            "corresponding file render without an "
            "analytical section. Only valid with an "
            "AgentScore record."
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


def _enforce_narrative_flag_compatibility(
    score: CaseScore | AgentScore,
    narrative_path: Path | None,
    narratives_dir: Path | None,
) -> None:
    if isinstance(score, AgentScore):
        if narrative_path is not None:
            raise _NarrativeFlagMisuseError(
                "--narrative is for CaseScore records; "
                "the score file is an AgentScore.\n"
                "To proceed: replace --narrative with "
                "--narratives-dir <dir> and supply per-"
                "case files named <case_id>.json under "
                "that directory."
            )
        return
    if narratives_dir is not None:
        raise _NarrativeFlagMisuseError(
            "--narratives-dir is for AgentScore "
            "records; the score file is a CaseScore.\n"
            "To proceed: replace --narratives-dir "
            "with --narrative <path> and supply the "
            "single CaseNarrative JSON file for this "
            "case."
        )


def _load_case_narrative_or_exit(
    narrative_path: Path,
) -> CaseNarrative:
    return load_case_narrative(narrative_path)


def _load_agent_narratives(
    narratives_dir: Path,
    score: AgentScore,
) -> dict[str, CaseNarrative]:
    if not narratives_dir.is_dir():
        raise _NarrativeFlagMisuseError(
            f"--narratives-dir does not point to a "
            f"directory: {narratives_dir}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path exists and is a "
            f"directory.\n"
            f"  (2) Re-invoke render_report.py with "
            f"the corrected path."
        )
    declared_ids = {
        case.case_id for case in score.case_scores
    }
    found: dict[str, Path] = {
        candidate.stem: candidate
        for candidate in sorted(
            narratives_dir.glob(
                f"*{_NARRATIVE_FILE_SUFFIX}"
            )
        )
        if candidate.is_file()
    }
    unknown = sorted(set(found) - declared_ids)
    if unknown:
        offending_paths = ", ".join(
            str(found[case_id]) for case_id in unknown
        )
        raise _NarrativeFlagMisuseError(
            f"--narratives-dir at {narratives_dir} "
            f"holds narrative file(s) for case id(s) "
            f"the agent score does not declare: "
            f"{unknown}.\n"
            f"Offending file(s): {offending_paths}\n"
            f"Declared case ids: "
            f"{sorted(declared_ids)}\n"
            f"To proceed:\n"
            f"  (1) Confirm the directory holds files "
            f"for the same cases the score covers. "
            f"The most common cause is reusing "
            f"narratives from an earlier run of a "
            f"different manifest.\n"
            f"  (2) Either delete the offending files "
            f"or move them to a different directory, "
            f"then re-invoke render_report.py."
        )
    bound: dict[str, CaseNarrative] = {}
    for case_id in sorted(declared_ids & set(found)):
        bound[case_id] = load_case_narrative(found[case_id])
    return bound


def _render(
    score: CaseScore | AgentScore,
    *,
    narrative: CaseNarrative | None,
    narratives: dict[str, CaseNarrative] | None,
) -> str:
    if isinstance(score, AgentScore):
        return render_agent_score_markdown(
            score, narratives=narratives
        )
    return render_case_score_markdown(
        score, narrative=narrative
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    try:
        score = _load_score(args.score.resolve())
    except _RenderReportError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    narrative_path = (
        args.narrative.resolve()
        if args.narrative is not None
        else None
    )
    narratives_dir = (
        args.narratives_dir.resolve()
        if args.narratives_dir is not None
        else None
    )

    try:
        _enforce_narrative_flag_compatibility(
            score=score,
            narrative_path=narrative_path,
            narratives_dir=narratives_dir,
        )
    except _RenderReportError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    narrative: CaseNarrative | None = None
    narratives: dict[str, CaseNarrative] | None = None
    try:
        if narrative_path is not None:
            narrative = _load_case_narrative_or_exit(
                narrative_path
            )
        elif narratives_dir is not None and isinstance(
            score, AgentScore
        ):
            narratives = _load_agent_narratives(
                narratives_dir, score
            )
    except CaseNarrativeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except _RenderReportError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        markdown = _render(
            score,
            narrative=narrative,
            narratives=narratives,
        )
    except UnresolvedCitationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except CaseNarrativeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
