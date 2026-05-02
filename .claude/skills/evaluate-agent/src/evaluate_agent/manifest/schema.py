"""
Pydantic schema for the agent manifest.
"""

from __future__ import annotations

from typing import Annotated, Literal

from evaluate_agent.common.types import StrictFrozen
from pydantic import (
    Field,
    HttpUrl,
    StringConstraints,
    model_validator,
)

Slug = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-z][a-z0-9_-]*$",
        min_length=1,
        max_length=64,
    ),
]

Identifier = Annotated[
    str,
    StringConstraints(
        pattern=r"^[A-Za-z_][A-Za-z0-9_.\-]*$",
        min_length=1,
        max_length=128,
    ),
]


class BearerAuth(StrictFrozen):
    type: Literal["bearer"] = "bearer"
    token_env: Annotated[
        str,
        Field(
            min_length=1,
            description="Environment variable holding the bearer token.",
        ),
    ]


class BasicAuth(StrictFrozen):
    type: Literal["basic"] = "basic"
    username_env: Annotated[
        str,
        Field(
            min_length=1,
            description="Environment variable holding the username.",
        ),
    ]
    password_env: Annotated[
        str,
        Field(
            min_length=1,
            description="Environment variable holding the password.",
        ),
    ]


Auth = Annotated[
    BearerAuth | BasicAuth,
    Field(discriminator="type"),
]


class WebAccess(StrictFrozen):
    url: Annotated[
        HttpUrl,
        Field(
            description="URL of the agent's user-facing web entry point."
        ),
    ]
    auth: Auth | None = None


class LangfuseSource(StrictFrozen):
    host: HttpUrl
    public_key_env: str = Field(
        default="LANGFUSE_PUBLIC_KEY", min_length=1
    )
    secret_key_env: str = Field(
        default="LANGFUSE_SECRET_KEY", min_length=1
    )


class OtelSource(StrictFrozen):
    endpoint: HttpUrl
    headers_env: str | None = Field(
        default=None, min_length=1
    )


UIExposedEvidence = Literal[
    "tool_calls",
    "routing_decisions",
    "step_count",
]


class UIIntrospectionSource(StrictFrozen):
    description: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Free-form description of WHERE the chat "
                "UI exposes the structured signal once "
                "reveal_actions have run. Read by the "
                "extracting sub-agent to locate and parse "
                "entries from the captured post-submit "
                "DOM. Be concrete: name the DOM region, "
                "the visual anchor, and the per-entry "
                "shape — e.g. 'each agent reply embeds a "
                '<details data-testid="reasoning-panel"> '
                "listing tool name, JSON arguments, and "
                "result per step in execution order'."
            ),
        ),
    ]
    reveal_actions: Annotated[
        list[Precondition],
        Field(
            default_factory=list,
            description=(
                "Ordered actions the driver runs AFTER "
                "case_input has been submitted and "
                "interaction.response_wait_ms has elapsed, "
                "but BEFORE capturing the post-submit DOM. "
                "Use these to expand a collapsed reasoning "
                "drawer, click a 'show details' toggle, or "
                "switch to a debug tab so the captured DOM "
                "contains the structured tool-call signal. "
                "Empty when the UI exposes the signal on "
                "every reply without a reveal step."
            ),
        ),
    ]
    exposes: Annotated[
        frozenset[UIExposedEvidence],
        Field(
            min_length=1,
            description=(
                "Evidence kinds the chat UI surfaces. "
                "Declare 'tool_calls' when the UI shows "
                "tool name + arguments per call (enables "
                "must_call / must_not_call), "
                "'routing_decisions' when the UI shows "
                "which sub-agent each step routed to "
                "(enables must_route_to), and 'step_count' "
                "when the UI shows a discrete reasoning-"
                "step counter (enables max_steps). "
                "Assertion kinds whose evidence is not "
                "exposed remain inconclusive with the "
                "standard recovery procedure."
            ),
        ),
    ]


class Observability(StrictFrozen):
    langfuse: LangfuseSource | None = None
    otel: OtelSource | None = None
    ui_introspection: UIIntrospectionSource | None = None


class Precondition(StrictFrozen):
    action: Literal["click", "select", "fill"]
    selector: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "CSS selector for the element the action "
                "targets on the chat URL's initial page."
            ),
        ),
    ]
    value: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "Value the action sets. Required for "
                "select (the option label or value) and "
                "fill (the literal text). Omitted for "
                "click."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _value_required_for_value_actions(
        self,
    ) -> "Precondition":
        if (
            self.action in ("select", "fill")
            and self.value is None
        ):
            raise ValueError(
                f"action {self.action!r} requires "
                f"value to be set"
            )
        if (
            self.action == "click"
            and self.value is not None
        ):
            raise ValueError(
                "action 'click' must not declare value"
            )
        return self


class InteractionConfig(StrictFrozen):
    preconditions: Annotated[
        list[Precondition],
        Field(
            default_factory=list,
            description=(
                "Ordered actions the driver runs before "
                "typing case.input — typically dropdown "
                "selects or modal dismissals required to "
                "reach a usable chat input on the agent's "
                "URL. Each action targets a CSS selector "
                "on the initial page; they run in "
                "declaration order, with a short wait "
                "between actions."
            ),
        ),
    ]
    input_selector: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description=(
                "CSS selector for the agent's primary "
                "input field. When set, the driver locates "
                "this element before typing case.input. "
                "When omitted, the driver falls back to "
                "the first visible <textarea>, then the "
                "first visible <input type='text'>."
            ),
        ),
    ]
    response_wait_ms: Annotated[
        int,
        Field(
            default=2000,
            ge=100,
            le=120_000,
            description=(
                "Milliseconds to wait after submitting "
                "case.input before capturing the "
                "post-submit screenshot. Tune up for "
                "agents whose response takes longer to "
                "render; tune down for fast agents. "
                "Lower bound of 100ms reserves enough "
                "time for any real agent's first byte "
                "of response — capturing earlier yields "
                "an unsubmitted-state DOM."
            ),
        ),
    ]


class Assertions(StrictFrozen):
    must_call: list[Identifier] = Field(
        default_factory=list
    )
    must_not_call: list[Identifier] = Field(
        default_factory=list
    )
    must_route_to: Identifier | None = None
    max_steps: int | None = Field(default=None, ge=1)
    final_response_contains: str | None = Field(
        default=None, min_length=1
    )
    max_total_tokens: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Inclusive upper bound on the sum of "
            "total_tokens across every Generation "
            "captured for the case. Resolves against "
            "generations.jsonl — trace-backend only "
            "(LangFuse / OTEL); chat UIs do not expose "
            "token counts so ui_introspection cannot "
            "supply this. Inconclusive when "
            "generations.jsonl is absent."
        ),
    )
    max_total_cost_usd: float | None = Field(
        default=None,
        gt=0,
        description=(
            "Inclusive upper bound on the sum of "
            "total_cost_usd across every Generation "
            "captured for the case. Resolves against "
            "generations.jsonl — trace-backend only. "
            "Inconclusive when generations.jsonl is "
            "absent OR when the captured generations "
            "carry no cost_details (some self-hosted "
            "LangFuse instances skip cost mapping)."
        ),
    )
    max_latency_ms: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Inclusive upper bound on the sum of "
            "latency_ms across every Generation "
            "captured for the case (total LLM-generation "
            "wall-clock time). Resolves against "
            "generations.jsonl — trace-backend only. "
            "Inconclusive when generations.jsonl is "
            "absent OR when generations carry no "
            "start/end timestamps."
        ),
    )

    @model_validator(mode="after")
    def _must_and_must_not_are_disjoint(
        self,
    ) -> "Assertions":
        overlap = set(self.must_call) & set(
            self.must_not_call
        )
        if overlap:
            raise ValueError(
                f"must_call and must_not_call overlap: {sorted(overlap)}"
            )
        return self


class Case(StrictFrozen):
    id: Slug
    input: Annotated[str, Field(min_length=1)]
    assertions: Assertions = Field(
        default_factory=Assertions
    )

    @model_validator(mode="after")
    def _at_least_one_assertion(self) -> "Case":
        a = self.assertions
        if not (
            a.must_call
            or a.must_not_call
            or a.must_route_to is not None
            or a.max_steps is not None
            or a.final_response_contains is not None
            or a.max_total_tokens is not None
            or a.max_total_cost_usd is not None
            or a.max_latency_ms is not None
        ):
            raise ValueError(
                f"case {self.id!r}: assertions block "
                f"declares no checks. Every case must "
                f"declare at least one assertion under "
                f"any of must_call, must_not_call, "
                f"must_route_to, max_steps, "
                f"final_response_contains, "
                f"max_total_tokens, max_total_cost_usd, "
                f"max_latency_ms — a case with no "
                f"checks would silently pass scoring."
            )
        return self


class AgentManifest(StrictFrozen):
    name: Slug
    description: str | None = Field(
        default=None, min_length=1, max_length=500
    )
    access: WebAccess
    observability: Observability = Field(
        default_factory=Observability
    )
    interaction: InteractionConfig = Field(
        default_factory=InteractionConfig
    )
    tools_catalog: list[Identifier] = Field(
        default_factory=list
    )
    agents_catalog: list[Identifier] = Field(
        default_factory=list
    )
    cases: list[Case] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _unique_case_ids(self) -> "AgentManifest":
        seen: set[str] = set()
        dups: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                dups.add(case.id)
            seen.add(case.id)
        if dups:
            raise ValueError(
                f"duplicate case ids: {sorted(dups)}"
            )
        return self

    @model_validator(mode="after")
    def _assertions_reference_declared_catalog_entries(
        self,
    ) -> "AgentManifest":
        if self.tools_catalog:
            allowed_tools = set(self.tools_catalog)
            for case in self.cases:
                for name in case.assertions.must_call:
                    if name not in allowed_tools:
                        raise ValueError(
                            f"case {case.id!r}: must_call references undeclared tool {name!r}"
                        )
                for name in case.assertions.must_not_call:
                    if name not in allowed_tools:
                        raise ValueError(
                            f"case {case.id!r}: must_not_call references undeclared tool {name!r}"
                        )
        if self.agents_catalog:
            allowed_agents = set(self.agents_catalog)
            for case in self.cases:
                target = case.assertions.must_route_to
                if (
                    target is not None
                    and target not in allowed_agents
                ):
                    raise ValueError(
                        f"case {case.id!r}: must_route_to references undeclared agent {target!r}"
                    )
        return self


__all__ = [
    "AgentManifest",
    "Assertions",
    "Auth",
    "BasicAuth",
    "BearerAuth",
    "Case",
    "Identifier",
    "InteractionConfig",
    "LangfuseSource",
    "Observability",
    "OtelSource",
    "Precondition",
    "Slug",
    "UIExposedEvidence",
    "UIIntrospectionSource",
    "WebAccess",
]
