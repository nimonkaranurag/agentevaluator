"""
Resolve LangFuse credentials from the manifest's declared env vars.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from evaluate_agent.common.errors.observability_fetchers import (
    LangfuseCredentialEnvVarMissing,
)
from evaluate_agent.manifest.schema import LangfuseSource


@dataclass(frozen=True)
class LangfuseCredentials:
    host: str
    public_key: str
    secret_key: str


def resolve_langfuse_credentials(
    source: LangfuseSource,
) -> LangfuseCredentials:
    return LangfuseCredentials(
        host=str(source.host).rstrip("/"),
        public_key=_require_env(
            env_var=source.public_key_env,
            role="public key",
        ),
        secret_key=_require_env(
            env_var=source.secret_key_env,
            role="secret key",
        ),
    )


def _require_env(*, env_var: str, role: str) -> str:
    value = os.environ.get(env_var)
    if not value:
        raise LangfuseCredentialEnvVarMissing(
            env_var=env_var,
            role=role,
        )
    return value


__all__ = [
    "LangfuseCredentials",
    "resolve_langfuse_credentials",
]
