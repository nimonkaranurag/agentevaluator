"""
Typed errors raised by the observability-fetcher layer.
"""

from __future__ import annotations

from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[4]
_ONBOARDING_GUIDE = _SKILL_ROOT / "SKILL.md"


class ObservabilityFetcherError(Exception):
    pass


class NoObservabilitySourceDeclared(
    ObservabilityFetcherError
):
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        super().__init__(
            f"Manifest at {manifest_path} declares "
            f"neither observability.langfuse nor "
            f"observability.otel, so the fetcher has no "
            f"backend to query.\n"
            f"To proceed:\n"
            f"  (1) Add an observability.langfuse "
            f"section if the agent's traces land in a "
            f"LangFuse host. The schema lives at "
            f"src/evaluate_agent/manifest/schema.py "
            f"(see LangfuseSource).\n"
            f"  (2) Add an observability.otel section if "
            f"the agent emits OpenTelemetry GenAI spans "
            f"to a Tempo-style query backend (see "
            f"OtelSource in the same schema file).\n"
            f"  (3) If neither trace backend applies, do "
            f"not invoke the fetcher; the four "
            f"observability-driven assertions resolve to "
            f"inconclusive without the on-disk logs, "
            f"with a recovery procedure naming the "
            f"absent path."
        )


class MultipleObservabilitySourcesDeclared(
    ObservabilityFetcherError
):
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        super().__init__(
            f"Manifest at {manifest_path} declares both "
            f"observability.langfuse and "
            f"observability.otel. The fetcher writes a "
            f"single set of canonical artifacts per "
            f"case, so two declared sources would race "
            f"to overwrite each other's output.\n"
            f"To proceed:\n"
            f"  (1) Keep the source that is authoritative "
            f"for this agent's traces and remove the "
            f"other from the manifest.\n"
            f"  (2) If the agent emits to BOTH backends "
            f"in production, pick the one richer in "
            f"GenAI semantic-convention attributes "
            f"(usually LangFuse) so the four "
            f"observability-driven assertions have the "
            f"most complete evidence."
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


class OtelHeadersEnvMissing(ObservabilityFetcherError):
    def __init__(self, env_var: str) -> None:
        self.env_var = env_var
        super().__init__(
            f"Environment variable {env_var!r} is not "
            f"set but observability.otel.headers_env "
            f"declares it as the source for the OTLP "
            f"query backend's auth headers.\n"
            f"To proceed:\n"
            f"  (1) Export the headers value as a "
            f"comma-separated key=value list: "
            f"`export {env_var}='Authorization=Bearer "
            f"<token>'` (multiple headers separated by "
            f"commas, no spaces around the `=`). This "
            f"matches the OTLP exporter convention used "
            f"by OTEL_EXPORTER_OTLP_HEADERS.\n"
            f"  (2) If the backend does not require "
            f"auth, remove headers_env from the "
            f"manifest's observability.otel block."
        )


class OtelHeadersMalformed(ObservabilityFetcherError):
    def __init__(
        self,
        *,
        env_var: str,
        offending_pair: str,
    ) -> None:
        self.env_var = env_var
        self.offending_pair = offending_pair
        super().__init__(
            f"Environment variable {env_var!r} held "
            f"value {offending_pair!r} that is not a "
            f"valid OTLP header. Expected a "
            f"comma-separated list of key=value pairs "
            f"(no spaces around the `=`), matching the "
            f"OTEL_EXPORTER_OTLP_HEADERS convention.\n"
            f"To proceed:\n"
            f"  (1) Re-export with a parseable value: "
            f"`export {env_var}='Authorization=Bearer "
            f"<token>,X-Tenant=acme'`.\n"
            f"  (2) Remove headers_env from "
            f"observability.otel if the backend does not "
            f"require auth."
        )


class OtelQueryFailed(ObservabilityFetcherError):
    def __init__(
        self,
        *,
        endpoint: str,
        operation: str,
        detail: str,
    ) -> None:
        self.endpoint = endpoint
        self.operation = operation
        self.detail = detail
        super().__init__(
            f"OTLP query {operation!r} against "
            f"{endpoint} failed.\n"
            f"Underlying detail: {detail}\n"
            f"To proceed:\n"
            f"  (1) Confirm the endpoint is reachable "
            f"from the machine running the fetcher "
            f"(e.g. `curl -I {endpoint}/api/echo`). The "
            f"OTEL fetcher targets a Tempo-style query "
            f"API exposing /api/search and "
            f"/api/traces/<id>; non-Tempo backends MUST "
            f"front them through a Tempo-compatible "
            f"shim.\n"
            f"  (2) If the underlying detail names an "
            f"HTTP 401 / 403, confirm "
            f"observability.otel.headers_env points at "
            f"an env var holding valid auth headers in "
            f"the OTEL_EXPORTER_OTLP_HEADERS format.\n"
            f"  (3) If the underlying detail names a "
            f"timeout, retry once. If it persists, "
            f"check the backend's health endpoint "
            f"before re-invoking.\n"
            f"  (4) See {_ONBOARDING_GUIDE} for the "
            f"observability-fetcher invocation surface."
        )


__all__ = [
    "LangfuseCredentialEnvVarMissing",
    "LangfuseQueryFailed",
    "MultipleObservabilitySourcesDeclared",
    "NoObservabilitySourceDeclared",
    "ObservabilityFetcherError",
    "OtelHeadersEnvMissing",
    "OtelHeadersMalformed",
    "OtelQueryFailed",
]
