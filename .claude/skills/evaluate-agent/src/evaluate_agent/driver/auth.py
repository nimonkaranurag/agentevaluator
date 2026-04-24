"""
Translate manifest access auth into Playwright new_context kwargs.
"""

from __future__ import annotations

import os
from typing import Any

from evaluate_agent.manifest.schema import (
    BasicAuth,
    BearerAuth,
    WebAccess,
)


class MissingAuthEnvVar(RuntimeError):
    def __init__(self, var: str) -> None:
        self.var = var
        super().__init__(
            f"Environment variable {var!r} is not set but is required by the manifest's access.auth configuration.\n"
            f"To proceed:\n"
            f"  (1) Export the credential value: `export {var}=<value>` (or set it in your shell profile).\n"
            f"  (2) Re-invoke the skill. If the credential is unavailable, remove or update the access.auth block in the manifest — never inline the literal secret."
        )


def context_kwargs_for(
    access: WebAccess,
) -> dict[str, Any]:
    auth = access.auth
    if auth is None:
        return {}
    if isinstance(auth, BearerAuth):
        token = _require_env(auth.token_env)
        return {
            "extra_http_headers": {
                "Authorization": f"Bearer {token}"
            }
        }
    if isinstance(auth, BasicAuth):
        return {
            "http_credentials": {
                "username": _require_env(
                    auth.username_env
                ),
                "password": _require_env(
                    auth.password_env
                ),
            }
        }
    raise AssertionError(
        f"Unreachable: unknown auth type {type(auth).__name__}"
    )


def _require_env(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        raise MissingAuthEnvVar(var)
    return value


__all__ = ["MissingAuthEnvVar", "context_kwargs_for"]
