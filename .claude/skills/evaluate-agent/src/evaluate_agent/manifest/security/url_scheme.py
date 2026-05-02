"""
Defense-in-depth scheme allowlist for the agent's primary access URL.
"""

from __future__ import annotations

from urllib.parse import urlsplit

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


__all__ = ["validate_web_access_scheme"]
