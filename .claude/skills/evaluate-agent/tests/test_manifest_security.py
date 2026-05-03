"""
Failure-mode tests for the manifest security primitives (URL scheme, env-var allowlist, SafeText, host policy).
"""

from __future__ import annotations

import pytest
from evaluate_agent.manifest.security.env_var_name import (
    EnvVarName,
)
from evaluate_agent.manifest.security.host_policy import (
    validate_host_against_policy,
)
from evaluate_agent.manifest.security.safe_text import (
    SafeText,
)
from evaluate_agent.manifest.security.url_scheme import (
    validate_web_access_scheme,
)
from pydantic import TypeAdapter, ValidationError

_ENV_VAR = TypeAdapter(EnvVarName)
_SAFE_TEXT = TypeAdapter(SafeText)


@pytest.mark.parametrize(
    "scheme",
    [
        "file",
        "chrome",
        "javascript",
        "data",
        "ftp",
        "gopher",
    ],
)
def test_url_scheme_rejects_non_http_schemes(
    scheme: str,
) -> None:
    with pytest.raises(ValueError) as info:
        validate_web_access_scheme(
            url=f"{scheme}://example.com/x",
            field_label="access.url",
        )
    assert "access.url" in str(info.value)
    assert scheme in str(info.value)


@pytest.mark.parametrize(
    "scheme", ["http", "https", "HTTPS"]
)
def test_url_scheme_accepts_http_and_https_case_insensitive(
    scheme: str,
) -> None:
    validate_web_access_scheme(
        url=f"{scheme}://example.com/",
        field_label="access.url",
    )


@pytest.mark.parametrize(
    "name", ["PATH", "HOME", "USER", "SHELL", "PWD"]
)
def test_env_var_rejects_local_environment_state(
    name: str,
) -> None:
    with pytest.raises(ValidationError) as info:
        _ENV_VAR.validate_python(name)
    assert name in str(info.value)
    assert "forbidden" in str(info.value)


@pytest.mark.parametrize(
    "name", ["LD_PRELOAD", "DYLD_INSERT_LIBRARIES"]
)
def test_env_var_rejects_dynamic_loader_prefixes(
    name: str,
) -> None:
    with pytest.raises(ValidationError) as info:
        _ENV_VAR.validate_python(name)
    assert "dynamic loader" in str(info.value)


def test_env_var_rejects_private_key_suffix() -> None:
    with pytest.raises(ValidationError) as info:
        _ENV_VAR.validate_python("DEPLOY_PRIVATE_KEY")
    assert "_PRIVATE_KEY" in str(info.value)
    assert "asymmetric key material" in str(info.value)


@pytest.mark.parametrize(
    "name",
    [
        "lowercase_var",
        "MIXED_Case",
        "1STARTS_WITH_DIGIT",
        "HAS-DASH",
        "HAS SPACE",
        "",
    ],
)
def test_env_var_rejects_non_canonical_names(
    name: str,
) -> None:
    with pytest.raises(ValidationError):
        _ENV_VAR.validate_python(name)


@pytest.mark.parametrize(
    "name",
    [
        "AGENT_BEARER_TOKEN",
        "LANGFUSE_PUBLIC_KEY",
        "X",
        "A1_2_3",
    ],
)
def test_env_var_accepts_canonical_names(
    name: str,
) -> None:
    assert _ENV_VAR.validate_python(name) == name


def test_safe_text_accepts_tab_and_newline() -> None:
    text = "first line\n\tindented\n"
    assert _SAFE_TEXT.validate_python(text) == text


@pytest.mark.parametrize(
    "control_byte",
    [
        "\x00",  # NUL — truncates C-strings downstream
        "\x07",  # BEL
        "\x1b",  # ESC — introduces ANSI sequences
        "\x1f",  # US — high end of C0 range
    ],
)
def test_safe_text_rejects_c0_control_codepoints(
    control_byte: str,
) -> None:
    with pytest.raises(ValidationError) as info:
        _SAFE_TEXT.validate_python(
            f"prefix{control_byte}suffix"
        )
    detail = str(info.value)
    assert "forbidden control character" in detail
    assert (
        f"U+{ord(control_byte):04X}".upper()
        in detail.upper()
    )


def test_safe_text_reports_offending_index() -> None:
    with pytest.raises(ValidationError) as info:
        _SAFE_TEXT.validate_python("ok\x00bad")
    assert "index 2" in str(info.value)


def test_host_policy_https_only_rejects_plaintext() -> None:
    with pytest.raises(ValueError) as info:
        validate_host_against_policy(
            url="http://cloud.langfuse.com",
            policy="https_only",
            field_label="observability.langfuse.host",
        )
    assert "observability.langfuse.host" in str(info.value)
    assert "https://" in str(info.value)


def test_host_policy_https_only_rejects_loopback_http() -> (
    None
):
    # Even loopback hosts are rejected under https_only — the policy
    # name is the contract; localhost dev must opt into the explicit
    # escape hatch rather than being silently accepted.
    with pytest.raises(ValueError):
        validate_host_against_policy(
            url="http://localhost:3010",
            policy="https_only",
            field_label="observability.langfuse.host",
        )


def test_host_policy_https_only_accepts_tls_endpoint() -> (
    None
):
    validate_host_against_policy(
        url="https://cloud.langfuse.com",
        policy="https_only",
        field_label="observability.langfuse.host",
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:3010",
        "http://127.0.0.1:8080/",
        "http://[::1]:3010/",
        "http://LOCALHOST",
    ],
)
def test_host_policy_loopback_accepts_loopback_addresses(
    url: str,
) -> None:
    validate_host_against_policy(
        url=url,
        policy="insecure_loopback_only",
        field_label="observability.langfuse.host",
    )


def test_host_policy_loopback_rejects_non_loopback_host() -> (
    None
):
    # The escape hatch only applies to loopback. A public hostname
    # under this policy MUST surface as an error so a misconfigured
    # manifest does not silently send credentials in plaintext.
    with pytest.raises(ValueError) as info:
        validate_host_against_policy(
            url="http://internal.example.com",
            policy="insecure_loopback_only",
            field_label="observability.langfuse.host",
        )
    assert "loopback" in str(info.value)
    assert "internal.example.com" in str(info.value)


def test_host_policy_loopback_rejects_https_scheme() -> (
    None
):
    # The loopback policy is plaintext-only. https://localhost
    # belongs under https_only and should push the user there.
    with pytest.raises(ValueError) as info:
        validate_host_against_policy(
            url="https://localhost",
            policy="insecure_loopback_only",
            field_label="observability.otel.endpoint",
        )
    assert "requires http://" in str(info.value)
