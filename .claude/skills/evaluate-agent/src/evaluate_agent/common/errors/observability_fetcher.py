"""
Typed errors raised by the observability-fetcher layer.
"""

from __future__ import annotations

from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[4]
_ONBOARDING_GUIDE = _SKILL_ROOT / "SKILL.md"


class ObservabilityFetcherError(Exception):
    pass


class LangfuseSourceNotDeclared(ObservabilityFetcherError):
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        super().__init__(
            f"Manifest at {manifest_path} does not "
            f"declare observability.langfuse, but the "
            f"LangFuse fetcher requires that block to "
            f"locate the host and credentials.\n"
            f"To proceed:\n"
            f"  (1) Add an observability.langfuse "
            f"section to the manifest with the host the "
            f"agent's traces land at, the env var "
            f"holding the public key, and the env var "
            f"holding the secret key. The schema lives "
            f"at src/evaluate_agent/manifest/schema.py "
            f"(see LangfuseSource).\n"
            f"  (2) If LangFuse is not the source for "
            f"this agent's observability, do not invoke "
            f"the LangFuse fetcher; the four "
            f"observability-driven assertions resolve "
            f"to inconclusive without the on-disk "
            f"observability logs, with a recovery "
            f"procedure naming the absent path."
        )


class LangfuseCredentialEnvVarMissing(
    ObservabilityFetcherError
):
    def __init__(
        self,
        *,
        env_var: str,
        role: str,
    ) -> None:
        self.env_var = env_var
        self.role = role
        super().__init__(
            f"Environment variable {env_var!r} is not "
            f"set but is required as the {role} for the "
            f"manifest's observability.langfuse "
            f"configuration.\n"
            f"To proceed:\n"
            f"  (1) Export the credential value: "
            f"`export {env_var}=<value>` (or set it in "
            f"your shell profile).\n"
            f"  (2) Re-invoke the fetcher. If the "
            f"credential is unavailable, do not invoke "
            f"the LangFuse fetcher; never inline the "
            f"literal secret into the manifest."
        )


class LangfuseQueryFailed(ObservabilityFetcherError):
    def __init__(
        self,
        *,
        host: str,
        operation: str,
        detail: str,
    ) -> None:
        self.host = host
        self.operation = operation
        self.detail = detail
        super().__init__(
            f"LangFuse query {operation!r} against "
            f"{host} failed.\n"
            f"Underlying detail: {detail}\n"
            f"To proceed:\n"
            f"  (1) Confirm the host is reachable from "
            f"the machine running the fetcher (e.g. "
            f"`curl -I {host}`).\n"
            f"  (2) If the underlying detail names an "
            f"HTTP 401 / 403, the credentials are "
            f"valid-but-unauthorised for this project; "
            f"confirm the public/secret key pair was "
            f"issued for the project the agent's traces "
            f"land in.\n"
            f"  (3) If the underlying detail names a "
            f"timeout, retry once. If it persists, "
            f"check the LangFuse host's status page "
            f"before re-invoking.\n"
            f"  (4) See {_ONBOARDING_GUIDE} for the "
            f"observability-fetcher invocation surface."
        )


__all__ = [
    "LangfuseCredentialEnvVarMissing",
    "LangfuseQueryFailed",
    "LangfuseSourceNotDeclared",
    "ObservabilityFetcherError",
]
