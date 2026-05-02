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

Optionally adds a baseline diff section. Use --baseline <path> with an
AgentScore record to compute a per-assertion diff against a prior
AgentScore (matched by (case_id, assertion_kind, target)). The diff
section enumerates assertions newly failing, newly inconclusive, newly
passing, introduced, and removed since the baseline. When the input
AgentScore already carries an embedded baseline_diff (from
score_agent.py --baseline), that embedded diff is rendered when
--baseline is omitted; --baseline overrides it by recomputing fresh
against the supplied baseline.

Autodetects whether the input is an AgentScore (presence of the
agent_name field) or a CaseScore. Diagnostic logging (errors, warnings)
is emitted on stderr in either text or JSON form, controlled by
--log-format.

Exits 0 once rendering completes. Exits 1 on a missing or malformed
score file, on a record that does not validate as either type, on a
narrative-flag misuse, on a baseline-flag misuse (a CaseScore with
--baseline; a baseline file that is not an AgentScore; a baseline
agent_name that does not match the current agent_name), on an
unresolved citation reported by either structural integrity check, or
on any narrative-grounding violation.

When --metrics PATH is supplied, the script writes a single JSON
document to PATH at completion that records per-phase wall-clock timing
(load_score, [load_narrative | load_narratives], [load_baseline,
compute_baseline_diff], render) and the script's exit status.
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
from evaluate_agent.common.errors.scoring import (  # noqa: E402
    BaselineAgentMismatchError,
)
from evaluate_agent.common.phase_metrics import (  # noqa: E402
    MetricsCollector,
)
from evaluate_agent.common.script_logging import (  # noqa: E402
    LOG_FORMATS,
    configure_script_logging,
)
from evaluate_agent.report import (  # noqa: E402
    UnresolvedCitationError,
    render_agent_score_markdown,
    render_case_score_markdown,
)
from evaluate_agent.scoring import (  # noqa: E402
    AgentScore,
    BaselineDiff,
    CaseScore,
    compute_baseline_diff,
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


class _BaselineFlagMisuseError(_RenderReportError):
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
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help=(
            "Path to a prior AgentScore JSON file. "
            "When set, the rendered report adds a "
            "Diff vs baseline section that pairs "
            "every current assertion outcome against "
            "the baseline outcome by (case_id, "
            "assertion_kind, target). Only valid with "
            "an AgentScore record. Overrides any "
            "baseline_diff embedded in the score."
        ),
    )
    parser.add_argument(
        "--log-format",
        choices=LOG_FORMATS,
        default="text",
        help=(
            "Format for diagnostic log records on "
            "stderr. Default: text. CI consumers "
            "should select json."
        ),
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=None,
        help=(
            "Path to write the per-phase timing JSON "
            "document to at script completion. Omit "
            "to skip metrics emission."
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


def _load_baseline_score(
    baseline_path: Path,
) -> AgentScore:
    if not baseline_path.is_file():
        raise _BaselineFlagMisuseError(
            f"Baseline AgentScore file does not "
            f"exist or is not a file: {baseline_path}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path matches the "
            f"JSON file score_agent.py emitted on a "
            f"prior run for the same agent.\n"
            f"  (2) Re-invoke without --baseline to "
            f"render the report without a diff "
            f"section, or correct the path and "
            f"re-invoke."
        )
    raw = baseline_path.read_text(encoding="utf-8")
    try:
        return AgentScore.model_validate_json(raw)
    except ValidationError as exc:
        raise _BaselineFlagMisuseError(
            f"Baseline file at {baseline_path} did "
            f"not validate against the AgentScore "
            f"schema.\n"
            f"Validation errors:\n{exc}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was produced "
            f"by an unmodified score_agent.py "
            f"invocation.\n"
            f"  (2) Re-run score_agent.py against "
            f"the baseline plan and overwrite the "
            f"file, then re-invoke render_report.py "
            f"--baseline."
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


def _enforce_baseline_flag_compatibility(
    score: CaseScore | AgentScore,
    baseline_path: Path | None,
) -> None:
    if baseline_path is None:
        return
    if isinstance(score, CaseScore):
        raise _BaselineFlagMisuseError(
            "--baseline is for AgentScore records; "
            "the score file is a CaseScore. Per-case "
            "diffs are not supported.\n"
            "To proceed: omit --baseline, or render "
            "the report against the agent-level "
            "score that aggregates this case."
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
    baseline_diff: BaselineDiff | None,
) -> str:
    if isinstance(score, AgentScore):
        return render_agent_score_markdown(
            score,
            narratives=narratives,
            baseline_diff=baseline_diff,
        )
    return render_case_score_markdown(
        score, narrative=narrative
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    logger = configure_script_logging(
        script_name="render_report",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(script_name="render_report")
    exit_code = 1
    try:
        try:
            with metrics.phase("load_score"):
                score = _load_score(args.score.resolve())
        except _RenderReportError as exc:
            logger.error("%s", exc)
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
        baseline_path = (
            args.baseline.resolve()
            if args.baseline is not None
            else None
        )

        try:
            _enforce_narrative_flag_compatibility(
                score=score,
                narrative_path=narrative_path,
                narratives_dir=narratives_dir,
            )
            _enforce_baseline_flag_compatibility(
                score=score,
                baseline_path=baseline_path,
            )
        except _RenderReportError as exc:
            logger.error("%s", exc)
            return 1

        narrative: CaseNarrative | None = None
        narratives: dict[str, CaseNarrative] | None = None
        try:
            if narrative_path is not None:
                with metrics.phase("load_narrative"):
                    narrative = (
                        _load_case_narrative_or_exit(
                            narrative_path
                        )
                    )
            elif narratives_dir is not None and isinstance(
                score, AgentScore
            ):
                with metrics.phase("load_narratives"):
                    narratives = _load_agent_narratives(
                        narratives_dir, score
                    )
        except CaseNarrativeError as exc:
            logger.error("%s", exc)
            return 1
        except _RenderReportError as exc:
            logger.error("%s", exc)
            return 1

        baseline_diff: BaselineDiff | None = None
        if baseline_path is not None and isinstance(
            score, AgentScore
        ):
            try:
                with metrics.phase("load_baseline"):
                    baseline_score = _load_baseline_score(
                        baseline_path
                    )
                with metrics.phase("compute_baseline_diff"):
                    baseline_diff = compute_baseline_diff(
                        baseline=baseline_score,
                        current=score,
                    )
            except _RenderReportError as exc:
                logger.error("%s", exc)
                return 1
            except BaselineAgentMismatchError as exc:
                logger.error("%s", exc)
                return 1

        try:
            with metrics.phase("render"):
                markdown = _render(
                    score,
                    narrative=narrative,
                    narratives=narratives,
                    baseline_diff=baseline_diff,
                )
        except UnresolvedCitationError as exc:
            logger.error("%s", exc)
            return 1
        except CaseNarrativeError as exc:
            logger.error("%s", exc)
            return 1
        sys.stdout.write(markdown)
        exit_code = 0
        return exit_code
    finally:
        metrics.emit_if_configured(
            args.metrics,
            exit_status=(
                "success" if exit_code == 0 else "error"
            ),
        )


if __name__ == "__main__":
    sys.exit(main())
