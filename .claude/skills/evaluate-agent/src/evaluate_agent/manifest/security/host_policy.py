"""
Scheme-and-host policy enforcement for observability source URLs.
"""

from __future__ import annotations

import ipaddress
from typing import Literal
from urllib.parse import urlsplit

# 'https_only' is the production-safe default: any non-loopback
# trace backend (cloud LangFuse, hosted OTEL collector) MUST be
# reached over TLS, otherwise a network-path attacker can rewrite
# the trace stream and the framework will write attacker-fabricated
# evidence to disk.
#
# 'insecure_loopback_only' is the explicit dev-time escape hatch:
# when a developer runs LangFuse locally (e.g.
# `orchestrate server start --with-langfuse` binds it to
# http://localhost:3010), forcing TLS would break their workflow.
# The policy permits http:// ONLY when the host resolves to a
# loopback address — a public HTTP endpoint cannot reuse this
# escape hatch even if the manifest tries to.
HostPolicy = Literal[
    "https_only",
    "insecure_loopback_only",
]

# String hostnames that the OS resolves to a loopback address.
# 'localhost' is the documented portable name; we lower-case
# inputs before comparison so 'LOCALHOST' and 'Localhost' resolve
# the same way.
_LOOPBACK_HOSTNAMES = frozenset({"localhost"})


def validate_host_against_policy(
    *,
    url: str,
    policy: HostPolicy,
    field_label: str,
) -> None:
    # urlsplit + .hostname normalises away ports and userinfo,
    # so we compare on the bare host only. Lowercasing the
    # scheme and host makes the policy case-insensitive in the
    # same way the URL spec is.
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()

    if policy == "https_only":
        # Reject every non-https scheme (including http://) so
        # the operator gets the same error regardless of which
        # disallowed scheme they used.
        if scheme != "https":
            raise ValueError(
                f"{field_label}: policy 'https_only' "
                f"requires https://, got {scheme}://. "
                f"Either reissue the URL over HTTPS, or "
                f"opt into 'insecure_loopback_only' for "
                f"local development against a loopback "
                f"endpoint."
            )
        return

    # insecure_loopback_only — both checks below must hold.
    if scheme != "http":
        # Catches https://localhost (legitimate, but the user
        # has told us they're on the dev escape hatch — push
        # them onto the matching policy) and exotic schemes
        # (file://, etc., which never make sense here).
        raise ValueError(
            f"{field_label}: policy "
            f"'insecure_loopback_only' requires http://, "
            f"got {scheme}://. The policy exists only as "
            f"a dev-time escape hatch for plaintext "
            f"traffic to a loopback host; production "
            f"traffic must declare 'https_only'."
        )
    if not _is_loopback_host(hostname):
        # Catches http://internal.example.com — the manifest
        # author may have declared the loopback policy by
        # mistake, intending to talk to a private LAN host.
        # Surfacing the host they typed gives them an
        # immediate fix.
        raise ValueError(
            f"{field_label}: policy "
            f"'insecure_loopback_only' requires the host "
            f"to resolve to a loopback address "
            f"(localhost, 127.0.0.0/8, or ::1); got "
            f"{hostname!r}. A non-loopback HTTP host "
            f"would send credentials in plaintext over "
            f"the network. Either move the trace backend "
            f"to HTTPS and declare 'https_only', or run "
            f"it on the loopback interface."
        )


def _is_loopback_host(hostname: str) -> bool:
    # Two-stage check: literal hostname strings ('localhost')
    # cannot be parsed as IP addresses, so we match them first.
    # Then we attempt IP parsing; ipaddress.is_loopback covers
    # 127.0.0.0/8 and ::1 by spec.
    if hostname in _LOOPBACK_HOSTNAMES:
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP literal and not in the hostname allowlist —
        # treat as a public DNS name.
        return False
    return address.is_loopback


__all__ = [
    "HostPolicy",
    "validate_host_against_policy",
]
