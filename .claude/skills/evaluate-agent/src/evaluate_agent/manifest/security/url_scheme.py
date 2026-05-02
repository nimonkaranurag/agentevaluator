"""
Defense-in-depth scheme allowlist for the agent's primary access URL.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import BaseModel, HttpUrl, ValidationError

# Pydantic.HttpUrl already excludes most hostile schemes today.
# This second check exists so that if HttpUrl ever loosens (or if
# the field is later swapped to a more permissive URL type),
# the rejection still fires. The forbidden cases this catches:
# file:// would let a manifest steer the driver at the local
# filesystem; chrome:// would point it at browser-internal pages;
# javascript: and data: would inject executable contexts into
# the navigation step.
_ALLOWED_SCHEMES = frozenset({"http", "https"})


def validate_web_access_scheme(
    *,
    url: str,
    field_label: str,
) -> None:
    # Lowercased so 'HTTPS://' and 'https://' resolve the same
    # way — schemes are case-insensitive per RFC 3986.
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"{field_label}: scheme {scheme!r} is not "
            f"in the allowlist "
            f"{sorted(_ALLOWED_SCHEMES)}. Schemes like "
            f"file://, chrome://, javascript:, and "
            f"data: would point the driver at the local "
            f"filesystem or an injected execution "
            f"context — the manifest must name a real "
            f"http(s):// agent endpoint."
        )


class _HttpUrlSchemeProbe(BaseModel):
    # Constructed once at module import to verify our assumed
    # contract with Pydantic.HttpUrl. Defining the field on its
    # own model (rather than poking at HttpUrl's internals) means
    # the probe exercises the same code path real manifests hit.
    url: HttpUrl


# Schemes Pydantic.HttpUrl is documented to reject. If a future
# upgrade quietly accepts any of these, the secondary guard above
# silently transitions from defense-in-depth to load-bearing — at
# which point its allowlist needs to be re-audited because we'd
# now be the only line of defense. The probe below crashes at
# import time so CI catches that transition instead of a user
# discovering it after a malicious manifest reaches the driver.
_HTTPURL_MUST_REJECT: tuple[str, ...] = (
    # local-filesystem driver hijack
    "file:///etc/passwd",
    # browser-internal pages
    "chrome://settings",
    # script-injection context
    "javascript:alert(1)",
    # embedded-content context
    "data:text/html,<script>alert(1)</script>",
    # non-http(s) network protocols — should never reach a driver
    # expecting a chat URL
    "ftp://example.com/",
    "gopher://example.com/",
)


def _verify_httpurl_contract() -> None:
    for hostile in _HTTPURL_MUST_REJECT:
        try:
            _HttpUrlSchemeProbe(url=hostile)
        except ValidationError:
            continue
        # Hard failure at import time — surfaces in CI on the
        # very next pipeline run after the offending dependency
        # bump. Message names the upstream contract that broke
        # so the operator knows to re-audit url_scheme's
        # allowlist before deciding whether to relax this probe.
        raise AssertionError(
            f"Pydantic.HttpUrl accepted "
            f"{hostile!r} — the upstream contract this "
            f"module relies on has changed. "
            f"validate_web_access_scheme is now the only "
            f"line of defense against this scheme; "
            f"re-audit the allowlist in "
            f"_ALLOWED_SCHEMES before relaxing this "
            f"probe."
        )


_verify_httpurl_contract()


__all__ = ["validate_web_access_scheme"]
