"""
Pydantic schema for the agent manifest.
"""

from __future__ import annotations

from typing import Annotated, Literal

from evaluate_agent.common.types import StrictFrozen
from evaluate_agent.manifest.security import (
    EnvVarName,
    HostPolicy,
    SafeText,
    validate_host_against_policy,
    validate_web_access_scheme,
)
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
    # EnvVarName binds the field to the SHELL_VAR_NAME shape and
    # rejects names whose contents are local-environment state
    # (PATH, HOME, ...) rather than auth material — so a manifest
    # cannot exfiltrate $PATH by aliasing it as a bearer token.
    token_env: Annotated[
        EnvVarName,
        Field(
            description=(
                "Environment variable holding the bearer "
                "token. Must match ^[A-Z][A-Z0-9_]*$ and "
                "must not name a forbidden variable "
                "(PATH, HOME, USER, SHELL, PWD, LD_*, "
                "DYLD_*, *_PRIVATE_KEY)."
            ),
        ),
    ]


class BasicAuth(StrictFrozen):
    type: Literal["basic"] = "basic"
    username_env: Annotated[
        EnvVarName,
        Field(
            description=(
                "Environment variable holding the basic-"
                "auth username. Same allowlist as "
                "BearerAuth.token_env."
            ),
        ),
    ]
    password_env: Annotated[
        EnvVarName,
        Field(
            description=(
                "Environment variable holding the basic-"
                "auth password. Same allowlist as "
                "BearerAuth.token_env."
            ),
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

    @model_validator(mode="after")
    def _scheme_is_allowlisted(self) -> "WebAccess":
        # Defense-in-depth on top of HttpUrl: re-checks the
        # scheme so a future loosening of HttpUrl can't silently
        # widen the attack surface to file:// / chrome:// /
        # javascript: / data: navigations.
        validate_web_access_scheme(
            url=str(self.url),
            field_label="access.url",
        )
        return self


class LangfuseSource(StrictFrozen):
    host: HttpUrl
    # host_policy fails closed: the default 'https_only' rejects
    # plaintext traffic to anything (including localhost), so a
    # manifest that omits this field cannot accidentally regress
    # into HTTP. Local-dev manifests must opt into the loopback
    # policy explicitly.
    host_policy: Annotated[
        HostPolicy,
        Field(
            default="https_only",
            description=(
                "Allowed combination of scheme and host "
                "for the LangFuse endpoint. 'https_only' "
                "(default) requires https:// regardless "
                "of host — production-safe. "
                "'insecure_loopback_only' permits http:// "
                "to a loopback host (localhost / "
                "127.0.0.0/8 / ::1) for local development "
                "against a self-hosted LangFuse; rejects "
                "any non-loopback host."
            ),
        ),
    ]
    public_key_env: EnvVarName = Field(
        default="LANGFUSE_PUBLIC_KEY",
        description=(
            "Environment variable holding the LangFuse "
            "public key. Same allowlist as "
            "BearerAuth.token_env."
        ),
    )
    secret_key_env: EnvVarName = Field(
        default="LANGFUSE_SECRET_KEY",
        description=(
            "Environment variable holding the LangFuse "
            "secret key. Same allowlist as "
            "BearerAuth.token_env."
        ),
    )

    @model_validator(mode="after")
    def _host_satisfies_policy(self) -> "LangfuseSource":
        # Cross-field check: the policy is satisfied by the
        # combination of scheme + host, so it can only run
        # after both values are bound. field_label echoes the
        # YAML path so the violation surfaces under
        # 'observability.langfuse.host' in the load error.
        validate_host_against_policy(
            url=str(self.host),
            policy=self.host_policy,
            field_label="observability.langfuse.host",
        )
        return self


class OtelSource(StrictFrozen):
    endpoint: HttpUrl
    host_policy: Annotated[
        HostPolicy,
        Field(
            default="https_only",
            description=(
                "Allowed combination of scheme and host "
                "for the OTEL collector endpoint. Same "
                "semantics as LangfuseSource.host_policy."
            ),
        ),
    ]
    headers_env: EnvVarName | None = Field(
        default=None,
        description=(
            "Optional environment variable holding the "
            "OTEL collector headers (typically "
            "OTEL_EXPORTER_OTLP_HEADERS shape). Same "
            "allowlist as BearerAuth.token_env."
        ),
    )

    @model_validator(mode="after")
    def _endpoint_satisfies_policy(self) -> "OtelSource":
        validate_host_against_policy(
            url=str(self.endpoint),
            policy=self.host_policy,
            field_label="observability.otel.endpoint",
        )
        return self


UIExposedEvidence = Literal[
    "tool_calls",
    "routing_decisions",
    "step_count",
]


class UIIntrospectionSource(StrictFrozen):
    # SafeText keeps free-form text out of the report's ANSI/
    # control-char attack surface — a description that smuggled
    # an ESC sequence would render as styled output in the
    # Markdown report and could mislead a human reviewer.
    description: Annotated[
        SafeText,
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
    # Selectors are technical strings rather than free prose,
    # but legitimate CSS never contains C0 control bytes — so
    # SafeText is a no-op for valid input and a clean rejection
    # for adversarial input that tries to smuggle ANSI through
    # the selector field into the rendered report.
    selector: Annotated[
        SafeText,
        Field(
            min_length=1,
            description=(
                "CSS selector for the element the action "
                "targets on the chat URL's initial page."
            ),
        ),
    ]
    value: Annotated[
        SafeText | None,
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
        SafeText | None,
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
    # Manifest-declared so two operators running the same
    # agent.yaml on different machines see identical scoring
    # behavior. Living in the manifest (instead of an env
    # var or CLI flag) keeps the cap reviewable in YAML and
    # the run reproducible across machines and CI workers.
    max_dom_bytes: Annotated[
        int,
        Field(
            default=25 * 1024 * 1024,
            ge=64 * 1024,
            le=500 * 1024 * 1024,
            description=(
                "Inclusive byte cap on the post-submit "
                "DOM snapshot the scoring layer parses. "
                "Snapshots above the cap resolve "
                "final_response_contains to inconclusive "
                "with DOMSnapshotTooLarge instead of "
                "loading the file into memory and risking "
                "an OOM on common machines. Default 25 "
                "MiB sizes for typical chat UIs; raise "
                "deliberately when the agent's reply "
                "legitimately renders into a long page "
                "and lower the value when running on "
                "memory-constrained CI workers."
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
    # SafeText on the substring guards the renderer: an attacker
    # who controls the manifest can't inject ANSI/NUL bytes that
    # would later be echoed verbatim into the Markdown report's
    # 'expected' / 'observed' citation block.
    final_response_contains: SafeText | None = Field(
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
    # case.input is what the driver types into the agent's chat
    # box — control bytes here would be typed verbatim and could
    # produce undefined behaviour in the agent's own input
    # parser. SafeText also keeps the input safe to echo into
    # the rendered report's case header.
    input: Annotated[SafeText, Field(min_length=1)]
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
    # The manifest description is rendered verbatim into the
    # report's preface and into discovery-listing output, so
    # SafeText is the same anti-ANSI guard that protects every
    # other free-form field that flows to the renderer.
    description: SafeText | None = Field(
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
