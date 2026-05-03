"""
Failure-mode tests for case-score composition, agent rollup composition, baseline diff, and the rollup partition validators.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import (
    write_generations,
    write_routing_decisions,
    write_step_count,
    write_tool_calls,
)
from evaluate_agent.common.errors.scoring import (
    BaselineAgentMismatchError,
)
from evaluate_agent.manifest.schema import (
    Assertions,
    CallSpec,
    Case,
)
from evaluate_agent.scoring.outcomes import (
    AssertionEvidence,
    AssertionFailed,
    AssertionPassed,
)
from evaluate_agent.scoring.scores import (
    AgentScore,
    CaseScore,
    compute_baseline_diff,
    score_agent,
    score_case,
)
from evaluate_agent.scoring.scores.rollups import (
    AgentRollup,
    AssertionKindRollup,
    AssertionTargetRollup,
    CaseOutcomeRollup,
)
from pydantic import ValidationError

_RUN_ID = "20260425T173000Z"


def _evidence(path: Path) -> AssertionEvidence:
    return AssertionEvidence(artifact_path=path, detail="x")


def _passed(
    kind: str,
    target: str | None,
    path: Path,
) -> AssertionPassed:
    return AssertionPassed(
        assertion_kind=kind,
        target=target,
        evidence=_evidence(path),
    )


def _failed(
    kind: str,
    target: str | None,
    path: Path,
) -> AssertionFailed:
    return AssertionFailed(
        assertion_kind=kind,
        target=target,
        expected="x",
        observed="y",
        evidence=_evidence(path),
    )


# ---------- score_case orchestration ----------


def test_score_case_emits_outcome_per_declared_assertion(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "lookup", "span_id": "s1"},
        ],
    )
    case = Case(
        id="c",
        input="hi",
        assertions=Assertions(
            must_call=["lookup"],
            must_not_call=["forbidden"],
            must_call_exactly={"lookup": 1},
        ),
    )
    score = score_case(
        case, case_dir, max_dom_bytes=1024 * 1024
    )
    assert score.case_id == "c"
    assert score.total == 3


def test_score_case_iterates_must_call_per_target(
    case_dir: Path,
) -> None:
    # Each tool in must_call produces its own outcome — the
    # rollup uses target-granularity to surface per-tool
    # pass/fail across cases. A regression that batched the
    # outcomes would lose target attribution.
    write_tool_calls(
        case_dir,
        [
            {"tool_name": "a", "span_id": "s1"},
        ],
    )
    case = Case(
        id="c",
        input="hi",
        assertions=Assertions(must_call=["a", "b"]),
    )
    score = score_case(
        case, case_dir, max_dom_bytes=1024 * 1024
    )
    targets = [o.target for o in score.outcomes]
    assert targets == ["a", "b"]


def test_score_case_must_call_with_args_uses_callspec(
    case_dir: Path,
) -> None:
    write_tool_calls(
        case_dir,
        [
            {
                "tool_name": "transfer",
                "span_id": "s1",
                "arguments": {"amount": 100},
            }
        ],
    )
    case = Case(
        id="c",
        input="hi",
        assertions=Assertions(
            must_call_with_args=[
                CallSpec(
                    tool_name="transfer",
                    args={"amount": 100},
                )
            ]
        ),
    )
    score = score_case(
        case, case_dir, max_dom_bytes=1024 * 1024
    )
    assert score.passed == 1


# ---------- agent rollup REGRESSION ----------


def test_agent_rollup_handles_every_assertion_kind(
    tmp_path: Path,
) -> None:
    # REGRESSION: ASSERTION_KIND_SCHEMA_ORDER previously named
    # only 5 of the 11 assertion kinds. _compose_rollup iterated
    # the constant when building by_assertion_kind, dropping
    # outcomes for must_call_exactly, must_call_with_args,
    # must_call_in_order, max_total_tokens, max_total_cost_usd,
    # and max_latency_ms — which then made the AgentRollup
    # validator (kind_total == total_assertions) raise on any
    # real manifest using those kinds. This regression test
    # forces every kind through the rollup so the constant
    # stays in sync with AssertionKind.
    case_dir = tmp_path / "case_a"
    case_dir.mkdir()
    cs = CaseScore(
        case_id="case_a",
        case_dir=case_dir,
        outcomes=(
            _passed(
                "final_response_contains", None, case_dir
            ),
            _passed("must_call", "lookup", case_dir),
            _passed("must_not_call", "forbidden", case_dir),
            _passed(
                "must_call_exactly", "lookup", case_dir
            ),
            _passed(
                "must_call_with_args", "transfer", case_dir
            ),
            _passed("must_call_in_order", None, case_dir),
            _passed("must_route_to", "billing", case_dir),
            _passed("max_steps", None, case_dir),
            _passed("max_total_tokens", None, case_dir),
            _passed("max_total_cost_usd", None, case_dir),
            _passed("max_latency_ms", None, case_dir),
        ),
    )
    score = score_agent(
        case_scores=(cs,),
        agent_name="demo",
        run_id=_RUN_ID,
        runs_root=tmp_path,
        manifest_path=tmp_path / "agent.yaml",
    )
    # Every kind must appear in by_assertion_kind. If the
    # constant drifts again, this assertion fails fast and
    # the validator below would crash before we get here.
    seen = {
        row.assertion_kind
        for row in score.rollup.by_assertion_kind
    }
    assert seen == {
        "final_response_contains",
        "must_call",
        "must_not_call",
        "must_call_exactly",
        "must_call_with_args",
        "must_call_in_order",
        "must_route_to",
        "max_steps",
        "max_total_tokens",
        "max_total_cost_usd",
        "max_latency_ms",
    }
    assert score.rollup.total_assertions == 11
    assert score.rollup.passed == 11


def test_agent_rollup_partitions_pass_fail_inconclusive(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case_a"
    case_dir.mkdir()
    cs = CaseScore(
        case_id="case_a",
        case_dir=case_dir,
        outcomes=(
            _passed("must_call", "a", case_dir),
            _failed("must_call", "b", case_dir),
        ),
    )
    score = score_agent(
        case_scores=(cs,),
        agent_name="demo",
        run_id=_RUN_ID,
        runs_root=tmp_path,
        manifest_path=tmp_path / "agent.yaml",
    )
    assert score.rollup.passed == 1
    assert score.rollup.failed == 1
    assert score.rollup.cases.with_any_failure == 1
    assert score.rollup.cases.fully_passed == 0


def test_agent_rollup_categorizes_no_assertions_case(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "empty"
    case_dir.mkdir()
    cs = CaseScore(
        case_id="empty",
        case_dir=case_dir,
        outcomes=(),
    )
    score = score_agent(
        case_scores=(cs,),
        agent_name="demo",
        run_id=_RUN_ID,
        runs_root=tmp_path,
        manifest_path=tmp_path / "agent.yaml",
    )
    assert score.rollup.cases.with_no_assertions == 1
    assert score.rollup.cases.fully_passed == 0


def test_agent_score_rejects_duplicate_case_ids(
    tmp_path: Path,
) -> None:
    # Two cases with the same id would silently merge in the
    # report; the schema cross-validator catches it.
    case_dir = tmp_path / "case_a"
    case_dir.mkdir()
    cs1 = CaseScore(
        case_id="dup",
        case_dir=case_dir,
        outcomes=(_passed("must_call", "a", case_dir),),
    )
    cs2 = CaseScore(
        case_id="dup",
        case_dir=case_dir,
        outcomes=(_passed("must_call", "b", case_dir),),
    )
    with pytest.raises(ValidationError) as info:
        AgentScore(
            agent_name="demo",
            run_id=_RUN_ID,
            runs_root=tmp_path,
            manifest_path=tmp_path / "agent.yaml",
            case_scores=(cs1, cs2),
            rollup=score_agent(
                case_scores=(cs1,),
                agent_name="demo",
                run_id=_RUN_ID,
                runs_root=tmp_path,
                manifest_path=tmp_path / "agent.yaml",
            ).rollup,
        )
    assert "duplicate case ids" in str(info.value)


# ---------- rollup validators ----------


def test_assertion_kind_rollup_validates_partition() -> (
    None
):
    with pytest.raises(ValidationError) as info:
        AssertionKindRollup(
            assertion_kind="must_call",
            total=5,
            passed=2,
            failed=2,
            inconclusive=2,
        )
    assert "do not partition" in str(info.value)


def test_assertion_target_rollup_validates_partition() -> (
    None
):
    # passed + failed + inconclusive must equal total. The
    # numbers below sum to 4, not 5, so the validator must
    # reject — guarding against a counter mishap that would
    # silently undercount in the report.
    with pytest.raises(ValidationError):
        AssertionTargetRollup(
            assertion_kind="must_call",
            target="lookup",
            total=5,
            passed=1,
            failed=1,
            inconclusive=2,
        )


def test_case_outcome_rollup_rejects_category_overflow() -> (
    None
):
    # Categories cannot exceed the total. Catches a regression
    # in the composer that double-counts a case across
    # exclusive categories.
    with pytest.raises(ValidationError):
        CaseOutcomeRollup(
            total=2,
            fully_passed=3,
            with_any_failure=0,
            with_any_inconclusive=0,
            with_no_assertions=0,
        )


# ---------- baseline diff ----------


def test_compute_baseline_diff_rejects_mismatched_agents(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case_a"
    case_dir.mkdir()
    cs = CaseScore(
        case_id="case_a",
        case_dir=case_dir,
        outcomes=(_passed("must_call", "a", case_dir),),
    )
    baseline = score_agent(
        case_scores=(cs,),
        agent_name="agent_one",
        run_id=_RUN_ID,
        runs_root=tmp_path,
        manifest_path=tmp_path / "agent.yaml",
    )
    current = score_agent(
        case_scores=(cs,),
        agent_name="agent_two",
        run_id=_RUN_ID,
        runs_root=tmp_path,
        manifest_path=tmp_path / "agent.yaml",
    )
    with pytest.raises(BaselineAgentMismatchError) as info:
        compute_baseline_diff(
            baseline=baseline, current=current
        )
    assert "agent_one" in str(info.value)
    assert "agent_two" in str(info.value)


def test_compute_baseline_diff_categorizes_transitions(
    tmp_path: Path,
) -> None:
    # Each AssertionTransition kind has a distinct narrative
    # role in the report; the diff must surface them so the
    # reader can answer "what changed since last run?".
    case_dir = tmp_path / "c"
    case_dir.mkdir()

    baseline = score_agent(
        case_scores=(
            CaseScore(
                case_id="c",
                case_dir=case_dir,
                outcomes=(
                    _failed("must_call", "stays", case_dir),
                    _passed(
                        "must_call", "regresses", case_dir
                    ),
                    _passed(
                        "must_call", "removed", case_dir
                    ),
                ),
            ),
        ),
        agent_name="demo",
        run_id="20260101T000000Z",
        runs_root=tmp_path,
        manifest_path=tmp_path / "agent.yaml",
    )
    current = score_agent(
        case_scores=(
            CaseScore(
                case_id="c",
                case_dir=case_dir,
                outcomes=(
                    _failed("must_call", "stays", case_dir),
                    _failed(
                        "must_call", "regresses", case_dir
                    ),
                    _passed(
                        "must_call", "introduced", case_dir
                    ),
                ),
            ),
        ),
        agent_name="demo",
        run_id="20260202T000000Z",
        runs_root=tmp_path,
        manifest_path=tmp_path / "agent.yaml",
    )
    diff = compute_baseline_diff(
        baseline=baseline, current=current
    )
    # BaselineDiff exposes one tuple per transition kind. The
    # contract: each (case_id, assertion_kind, target) triple
    # appears in exactly one tuple — the renderer relies on
    # that partition.
    assert {d.target for d in diff.newly_failing} == {
        "regresses"
    }
    assert {d.target for d in diff.removed} == {"removed"}
    assert {d.target for d in diff.introduced} == {
        "introduced"
    }
    assert {d.target for d in diff.unchanged} == {"stays"}
