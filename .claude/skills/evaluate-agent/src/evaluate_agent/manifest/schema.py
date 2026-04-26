"""
Pydantic schema for the agent manifest.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
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
        pattern=r"^[A-Za-z_][\w.\-]*$",
        min_length=1,
        max_length=128,
    ),
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BearerAuth(_Strict):
    type: Literal["bearer"] = "bearer"
    token_env: Annotated[
        str,
        Field(
            min_length=1,
            description="Environment variable holding the bearer token.",
        ),
    ]


class BasicAuth(_Strict):
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


class WebAccess(_Strict):
    url: Annotated[
        HttpUrl,
        Field(
            description="URL of the agent's user-facing web entry point."
        ),
    ]
    auth: Auth | None = None


class LangfuseSource(_Strict):
    host: HttpUrl
    public_key_env: str = Field(
        default="LANGFUSE_PUBLIC_KEY", min_length=1
    )
    secret_key_env: str = Field(
        default="LANGFUSE_SECRET_KEY", min_length=1
    )


class OtelSource(_Strict):
    endpoint: HttpUrl
    headers_env: str | None = Field(
        default=None, min_length=1
    )


class Observability(_Strict):
    langfuse: LangfuseSource | None = None
    otel: OtelSource | None = None


class InteractionConfig(_Strict):
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
            ge=0,
            le=120_000,
            description=(
                "Milliseconds to wait after submitting "
                "case.input before capturing the "
                "post-submit screenshot. Tune up for "
                "agents whose response takes longer to "
                "render; tune down for fast agents."
            ),
        ),
    ]


class Assertions(_Strict):
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


class Case(_Strict):
    id: Slug
    input: Annotated[str, Field(min_length=1)]
    assertions: Assertions = Field(
        default_factory=Assertions
    )


class AgentManifest(_Strict):
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
    "Slug",
    "WebAccess",
]
