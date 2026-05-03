"""
On-disk schemas for the structured observability logs the evaluators consume.
"""

from __future__ import annotations

from typing import Annotated, Any

from evaluate_agent.common.types import StrictFrozen
from pydantic import (
    Field,
    NonNegativeInt,
    model_validator,
)


class ToolCall(StrictFrozen):
    tool_name: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Name of the tool the agent invoked. "
                "Matched verbatim against must_call / "
                "must_not_call assertion targets."
            ),
        ),
    ]
    span_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Identifier of the span recording this "
                "tool call in the source observability "
                "system. Cited verbatim by passed and "
                "failed outcomes so a reader can locate "
                "the underlying span."
            ),
        ),
    ]
    arguments: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description=(
                "Arguments the agent passed to the tool. "
                "Captured for analytical context; the "
                "scoring layer does not match against "
                "argument shape."
            ),
        ),
    ]
    result: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Stringified result the tool returned to "
                "the agent. Captured for analytical "
                "context."
            ),
        ),
    ]
    timestamp: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "ISO-8601 timestamp recorded against the "
                "span. Optional because not every "
                "observability source emits a timestamp "
                "per tool call."
            ),
        ),
    ]


class RoutingDecision(StrictFrozen):
    target_agent: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Name of the sub-agent the routing "
                "decision selected. Matched verbatim "
                "against the must_route_to assertion "
                "target."
            ),
        ),
    ]
    span_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Identifier of the span recording this "
                "routing decision in the source "
                "observability system. Cited verbatim by "
                "passed and failed outcomes."
            ),
        ),
    ]
    from_agent: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Name of the agent that issued the "
                "routing decision, when the source "
                "records it. Captured for analytical "
                "context; the scoring layer does not "
                "match against it."
            ),
        ),
    ]
    reason: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Free-form rationale the agent recorded "
                "for the routing decision, when the "
                "source captures it. Used by the "
                "analytical narrative layer; the scoring "
                "layer does not match against it."
            ),
        ),
    ]
    timestamp: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "ISO-8601 timestamp recorded against the "
                "span. Optional because not every "
                "observability source emits a timestamp "
                "per routing decision."
            ),
        ),
    ]


class StepCount(StrictFrozen):
    total_steps: Annotated[
        NonNegativeInt,
        Field(
            description=(
                "Number of agent reasoning steps "
                "observed for the case. Compared "
                "directly against the max_steps "
                "assertion limit."
            ),
        ),
    ]
    step_span_ids: Annotated[
        tuple[str, ...],
        Field(
            description=(
                "Identifiers of the spans recording "
                "each agent step in the source "
                "observability system, listed in "
                "execution order. Cited verbatim by "
                "passed and failed outcomes."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _step_span_ids_match_total_steps(
        self,
    ) -> "StepCount":
        if len(self.step_span_ids) != self.total_steps:
            raise ValueError(
                f"step_span_ids length "
                f"({len(self.step_span_ids)}) does not "
                f"match total_steps "
                f"({self.total_steps}). Each observed "
                f"step must contribute exactly one span "
                f"id; emit one span id per step or "
                f"correct total_steps to match the "
                f"emitted ids.\nTo proceed:\n"
                f"  (1) Confirm the source observability "
                f"system emits one span per agent "
                f"reasoning step.\n"
                f"  (2) Regenerate the step_count.json "
                f"so total_steps equals the length of "
                f"step_span_ids."
            )
        for span_id in self.step_span_ids:
            if not span_id:
                raise ValueError(
                    "step_span_ids entries must be "
                    "non-empty strings; an empty span "
                    "id cannot anchor a citation."
                )
        return self


class Generation(StrictFrozen):
    span_id: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Identifier of the span recording this "
                "generation in the source observability "
                "system. Cited verbatim by passed and "
                "failed outcomes so a reader can locate "
                "the underlying generation. Required."
            ),
        ),
    ]
    model: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Name of the model that produced the "
                "generation, when the source records it. "
                "Captured for analytical context; the "
                "scoring layer does not match against it."
            ),
        ),
    ]
    input_tokens: Annotated[
        NonNegativeInt | None,
        Field(
            default=None,
            description=(
                "Tokens consumed by the prompt for this "
                "generation, when the source records "
                "usage. None when usage is not emitted "
                "for this model / configuration."
            ),
        ),
    ]
    output_tokens: Annotated[
        NonNegativeInt | None,
        Field(
            default=None,
            description=(
                "Tokens produced by the model for this "
                "generation, when the source records "
                "usage. None when usage is not emitted "
                "for this model / configuration."
            ),
        ),
    ]
    total_tokens: Annotated[
        NonNegativeInt | None,
        Field(
            default=None,
            description=(
                "Total tokens (input + output) for this "
                "generation. The max_total_tokens "
                "assertion sums this across the case's "
                "generations."
            ),
        ),
    ]
    input_cost_usd: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description=(
                "USD cost attributed to the prompt for "
                "this generation, when the source emits "
                "cost details."
            ),
        ),
    ]
    output_cost_usd: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description=(
                "USD cost attributed to the completion "
                "for this generation, when the source "
                "emits cost details."
            ),
        ),
    ]
    total_cost_usd: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description=(
                "Total USD cost (input + output) for "
                "this generation. The max_total_cost_usd "
                "assertion sums this across the case's "
                "generations."
            ),
        ),
    ]
    started_at: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "ISO-8601 start timestamp of the "
                "generation. Paired with ended_at to "
                "anchor the generation on the case's "
                "wall-clock timeline; the max_latency_ms "
                "assertion takes the earliest started_at "
                "across the case's generations as the "
                "lower bound of the wall-clock interval. "
                "Optional because not every observability "
                "source emits a start timestamp."
            ),
        ),
    ]
    ended_at: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "ISO-8601 end timestamp of the "
                "generation. Paired with started_at; the "
                "max_latency_ms assertion takes the "
                "latest ended_at across the case's "
                "generations as the upper bound of the "
                "wall-clock interval. Optional because "
                "not every observability source emits an "
                "end timestamp."
            ),
        ),
    ]


__all__ = [
    "Generation",
    "RoutingDecision",
    "StepCount",
    "ToolCall",
]
