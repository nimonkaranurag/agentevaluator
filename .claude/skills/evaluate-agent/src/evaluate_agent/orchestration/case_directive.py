"""
Per-case driving directive a sub-agent executes via the Playwright MCP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.schema import (
    Precondition,
    Slug,
    UIIntrospectionSource,
)
from pydantic import Field, HttpUrl


class CaseDirective(StrictFrozen):
    case_id: Annotated[
        Slug,
        Field(
            description=(
                "Case identifier copied from "
                "manifest.cases[].id. The sub-agent uses "
                "this as its own scope label and writes "
                "every captured artifact under the "
                "matching case_dir."
            ),
        ),
    ]
    case_dir: Annotated[
        Path,
        Field(
            description=(
                "Absolute path to the directory at "
                "<runs_root>/<agent_name>/<run_id>/"
                "<case_id> where the sub-agent writes "
                "every captured screenshot, DOM "
                "snapshot, and downstream artifact for "
                "this case."
            ),
        ),
    ]
    url: Annotated[
        HttpUrl,
        Field(
            description=(
                "Web URL the sub-agent navigates to via "
                "its MCP browser. Mirrors "
                "manifest.access.url verbatim."
            ),
        ),
    ]
    case_input: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Literal text the sub-agent types into "
                "the agent's input field. Mirrors "
                "manifest.cases[].input verbatim."
            ),
        ),
    ]
    input_selector: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "CSS selector the sub-agent uses to "
                "locate the agent's primary input field "
                "before typing case_input. Mirrors "
                "manifest.interaction.input_selector. "
                "None means the sub-agent falls back to "
                "the heuristic textarea -> input order."
            ),
        ),
    ]
    preconditions: Annotated[
        tuple[Precondition, ...],
        Field(
            default_factory=tuple,
            description=(
                "Ordered actions the sub-agent runs "
                "after navigating to url and before "
                "typing case_input. Mirrors "
                "manifest.interaction.preconditions in "
                "declaration order."
            ),
        ),
    ]
    response_wait_ms: Annotated[
        int,
        Field(
            ge=0,
            le=120_000,
            description=(
                "Milliseconds the sub-agent waits after "
                "submitting case_input before capturing "
                "the post-submit screenshot and DOM. "
                "Mirrors manifest.interaction."
                "response_wait_ms verbatim."
            ),
        ),
    ]
    landing_screenshot_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the sub-agent writes the "
                "landing-page screenshot to."
            ),
        ),
    ]
    landing_dom_snapshot_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the sub-agent writes the "
                "landing-page DOM HTML to."
            ),
        ),
    ]
    after_submit_screenshot_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the sub-agent writes the "
                "post-submit screenshot to."
            ),
        ),
    ]
    after_submit_dom_snapshot_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the sub-agent writes the "
                "post-submit DOM HTML to. The scoring "
                "layer reads this file to evaluate "
                "final_response_contains."
            ),
        ),
    ]
    ui_introspection: Annotated[
        UIIntrospectionSource | None,
        Field(
            default=None,
            description=(
                "Mirrors manifest.observability."
                "ui_introspection verbatim. When set, the "
                "sub-agent runs ui_introspection."
                "reveal_actions AFTER submitting "
                "case_input + waiting response_wait_ms but "
                "BEFORE capturing the post-submit DOM, "
                "then extracts entries described by "
                "ui_introspection.description from the "
                "captured DOM and writes them to "
                "tool_call_log_path / "
                "routing_decision_log_path / "
                "step_count_path per ui_introspection."
                "exposes. None means UI introspection is "
                "not declared and only structured trace "
                "sources (langfuse) populate the "
                "observability logs."
            ),
        ),
    ]
    tool_call_log_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the sub-agent writes the "
                "extracted tool-call JSONL to when "
                "ui_introspection is set and "
                "ui_introspection.exposes contains "
                "'tool_calls'. Mirrors the path the "
                "scoring layer reads to evaluate "
                "must_call / must_not_call."
            ),
        ),
    ]
    routing_decision_log_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the sub-agent writes the "
                "extracted routing-decision JSONL to when "
                "ui_introspection is set and "
                "ui_introspection.exposes contains "
                "'routing_decisions'. Mirrors the path "
                "the scoring layer reads to evaluate "
                "must_route_to."
            ),
        ),
    ]
    step_count_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path the sub-agent writes the "
                "extracted step-count JSON to when "
                "ui_introspection is set and "
                "ui_introspection.exposes contains "
                "'step_count'. Mirrors the path the "
                "scoring layer reads to evaluate "
                "max_steps."
            ),
        ),
    ]
    generation_log_path: Annotated[
        Path,
        Field(
            description=(
                "Absolute path where fetch_observability."
                "py writes the per-generation observability "
                "log (token usage, cost, latency per LLM "
                "generation) when manifest.observability."
                "langfuse is declared. Read by the "
                "max_total_tokens / max_total_cost_usd / "
                "max_latency_ms evaluators. UI "
                "introspection does not write to this "
                "path — chat UIs do not expose token "
                "counts or costs."
            ),
        ),
    ]


__all__ = ["CaseDirective"]
