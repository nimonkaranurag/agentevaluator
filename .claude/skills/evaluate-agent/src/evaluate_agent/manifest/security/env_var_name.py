"""
Allowlist-bounded environment variable name type for manifest credential fields.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, StringConstraints

# Regex shape: starts with an uppercase ASCII letter, remainder is
# uppercase ASCII letters, digits, or underscores. Mirrors the
# conventional shell env-var convention. The ASCII restriction
# closes the same homoglyph-bypass class that Identifier closed in
# session 1: a Cyrillic 'А' rendered as 'A' would otherwise reach
# os.environ lookup and find a different (or absent) variable.
_ENV_VAR_PATTERN = r"^[A-Z][A-Z0-9_]*$"

# Names whose contents are local-environment state that must never
# be resolved and forwarded to an upstream agent. PATH/HOME/USER/
# SHELL/PWD leak machine-local context (working directory, login
# name, default shell). The framework reads these as if they were
# bearer tokens and sends them in the Authorization header.
_FORBIDDEN_NAMES = frozenset(
    {
        "PATH",
        "HOME",
        "USER",
        "SHELL",
        "PWD",
    }
)

# Prefix-bounded forbidden families: these env-vars govern the
# dynamic loader on Linux (LD_*) and macOS (DYLD_*). Their values
# control which shared libraries get injected into every child
# process; sending those strings as auth tokens leaks the
# system's library-injection state to the upstream agent and to
# whatever logs the agent emits.
_FORBIDDEN_PREFIXES = ("LD_", "DYLD_")

# Suffix-bounded forbidden families: by convention any env-var
# ending in _PRIVATE_KEY holds asymmetric key material (SSH keys,
# RSA keys, signing keys). The framework must not forward such
# material as a bearer or basic credential — wrong shape, wrong
# trust boundary.
_FORBIDDEN_SUFFIXES = ("_PRIVATE_KEY",)


def _reject_forbidden_env_var(name: str) -> str:
    # Membership check first because exact-match diagnostics give
    # the user the cleanest signal: "PATH is forbidden, pick
    # another name" beats "starts with PA which..."
    if name in _FORBIDDEN_NAMES:
        raise ValueError(
            f"env-var name {name!r} is in the "
            f"forbidden list "
            f"{sorted(_FORBIDDEN_NAMES)} — these "
            f"variables hold local-environment state "
            f"that must not be forwarded to an upstream "
            f"agent as a credential. Pick a manifest-"
            f"specific name (e.g. AGENT_BEARER_TOKEN)."
        )
    for prefix in _FORBIDDEN_PREFIXES:
        if name.startswith(prefix):
            raise ValueError(
                f"env-var name {name!r} starts with "
                f"{prefix!r} — this prefix governs the "
                f"dynamic loader and its value would "
                f"expose library-injection state when "
                f"sent as a credential. Pick a "
                f"manifest-specific name."
            )
    for suffix in _FORBIDDEN_SUFFIXES:
        if name.endswith(suffix):
            raise ValueError(
                f"env-var name {name!r} ends with "
                f"{suffix!r} — this suffix conventionally "
                f"holds asymmetric key material, which "
                f"must not be forwarded as a bearer/"
                f"basic credential. Pick a manifest-"
                f"specific name."
            )
    return name


# Composition order: pattern + length checks first (cheap, give
# the most specific structural error), then the allowlist check
# (semantic policy on a string that already has the right shape).
EnvVarName = Annotated[
    str,
    StringConstraints(
        pattern=_ENV_VAR_PATTERN,
        min_length=1,
        max_length=128,
    ),
    AfterValidator(_reject_forbidden_env_var),
]


__all__ = ["EnvVarName"]
