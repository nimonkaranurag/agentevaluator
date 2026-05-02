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
Validate a case narrative against the case score it is bound to.

Loads a CaseNarrative JSON file and a CaseScore JSON file, verifies that
the narrative's case_id matches the score's case_id, and verifies that
every citation inside the narrative resolves to a real file under the
score's case_dir. Prints a formal success block on stdout when the
narrative is grounded.

Diagnostic logging (errors, warnings) is emitted on stderr in either
text or JSON form, controlled by --log-format.

Exits 0 when the narrative is grounded; 1 on any score-load,
narrative-load, or grounding failure (logged to stderr with the
actionable recovery procedure embedded in the message).

When --metrics PATH is supplied, the script writes a single JSON
document to PATH at completion that records per-phase wall-clock timing
(load_score, load_narrative, verify), the script's exit status, and
contextual identifiers (case_id).
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
    load_case_narrative,
    verify_narrative_against_score,
)
from evaluate_agent.common.errors.case_narrative import (  # noqa: E402
    CaseNarrativeError,
)
from evaluate_agent.common.phase_metrics import (  # noqa: E402
    MetricsCollector,
)
from evaluate_agent.common.script_logging import (  # noqa: E402
    LOG_FORMATS,
    configure_script_logging,
)
from evaluate_agent.scoring import (  # noqa: E402
    CaseScore,
)


class _ValidateNarrativeError(Exception):
    """
    Base for actionable failures the script reports to stderr.
    """


class _ScoreLoadError(_ValidateNarrativeError):
    pass


def _parse_args(
    argv: list[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="validate_narrative",
        description=(
            "Validate that a case narrative's case_id "
            "matches the bound score and every "
            "citation inside the narrative resolves to "
            "a real file under the score's case_dir."
        ),
    )
    parser.add_argument(
        "narrative",
        type=Path,
        help=(
            "Path to the JSON file produced by the "
            "synthesis step. The file must validate "
            "against the CaseNarrative schema."
        ),
    )
    parser.add_argument(
        "--score",
        required=True,
        type=Path,
        help=(
            "Path to the CaseScore JSON file the "
            "narrative is bound to (the JSON emitted on "
            "stdout by score_case.py). Narratives are "
            "always validated against a single case "
            "score, never against an AgentScore."
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


def _load_score(score_path: Path) -> CaseScore:
    if not score_path.is_file():
        raise _ScoreLoadError(
            f"Case score file does not exist or is "
            f"not a file: {score_path}\n"
            f"To proceed:\n"
            f"  (1) Confirm the path matches the file "
            f"score_case.py wrote (the JSON emitted on "
            f"its stdout).\n"
            f"  (2) If the score was never persisted, "
            f"run score_case.py and pipe its stdout to "
            f"a file, then re-invoke "
            f"validate_narrative.py with that file "
            f"path."
        )
    raw = score_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _ScoreLoadError(
            f"Case score file at {score_path} is not "
            f"valid JSON.\n"
            f"Parser detail: {exc}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was written "
            f"verbatim from score_case.py's stdout (no "
            f"truncation, no shell interpolation).\n"
            f"  (2) Re-run score_case.py and overwrite "
            f"the file, then re-invoke "
            f"validate_narrative.py."
        ) from exc

    if not isinstance(data, dict):
        raise _ScoreLoadError(
            f"Case score file at {score_path} parsed "
            f"as {type(data).__name__}, not a JSON "
            f"object. CaseScore records are JSON "
            f"objects.\n"
            f"To proceed: confirm the file was written "
            f"verbatim from score_case.py and "
            f"re-invoke validate_narrative.py."
        )

    if "agent_name" in data:
        raise _ScoreLoadError(
            f"Case score file at {score_path} is an "
            f"AgentScore record, not a CaseScore. "
            f"Narratives are always validated against "
            f"a single case score.\n"
            f"To proceed:\n"
            f"  (1) Re-run score_case.py against the "
            f"specific case the narrative explains "
            f"(`score_case.py <manifest> --case "
            f"<case_id> --case-dir <case-dir>`) and "
            f"capture its stdout.\n"
            f"  (2) Re-invoke validate_narrative.py "
            f"with the per-case CaseScore JSON."
        )

    try:
        return CaseScore.model_validate(data)
    except ValidationError as exc:
        raise _ScoreLoadError(
            f"Case score file at {score_path} did not "
            f"validate against the CaseScore schema.\n"
            f"Validation errors:\n{exc}\n"
            f"To proceed:\n"
            f"  (1) Confirm the file was produced by "
            f"an unmodified score_case.py.\n"
            f"  (2) Re-run score_case.py against the "
            f"same inputs and overwrite the file, "
            f"then re-invoke validate_narrative.py."
        ) from exc


def _print_success_block(
    narrative_path: Path,
    score_path: Path,
    score: CaseScore,
    citations_count: int,
) -> None:
    print(
        "\n".join(
            [
                "Case narrative validation: GROUNDED",
                f"  narrative: {narrative_path}",
                f"  score: {score_path}",
                f"  case_id: {score.case_id}",
                f"  case_dir: {score.case_dir}",
                f"  citations_resolved: "
                f"{citations_count}",
            ]
        )
    )


def _count_citations(narrative_path: Path) -> int:
    raw = narrative_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return sum(
        len(observation.get("citations", []))
        for observation in data.get("observations", [])
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    logger = configure_script_logging(
        script_name="validate_narrative",
        log_format=args.log_format,
    )
    metrics = MetricsCollector(
        script_name="validate_narrative"
    )
    exit_code = 1
    try:
        try:
            with metrics.phase("load_score"):
                score = _load_score(args.score.resolve())
        except _ValidateNarrativeError as exc:
            logger.error("%s", exc)
            return 1
        metrics.set_context(case_id=score.case_id)
        try:
            with metrics.phase("load_narrative"):
                narrative = load_case_narrative(
                    args.narrative.resolve()
                )
        except CaseNarrativeError as exc:
            logger.error("%s", exc)
            return 1
        try:
            with metrics.phase("verify"):
                verify_narrative_against_score(
                    narrative, score=score
                )
        except CaseNarrativeError as exc:
            logger.error("%s", exc)
            return 1
        _print_success_block(
            narrative_path=args.narrative.resolve(),
            score_path=args.score.resolve(),
            score=score,
            citations_count=_count_citations(
                args.narrative.resolve()
            ),
        )
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
