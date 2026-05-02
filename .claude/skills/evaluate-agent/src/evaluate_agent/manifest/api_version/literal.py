"""
ApiVersion literal types and the registry of currently-supported versions.
"""

from __future__ import annotations

from typing import Literal

# Per-version literal type. The pattern is one literal alias per
# version (ApiVersionV1 today, ApiVersionV2 when v2 ships) so that
# every versioned AgentManifest model can pin its apiVersion field
# to its own literal — making the union of versioned models a true
# discriminated union once a second variant exists.
ApiVersionV1 = Literal["agentevaluator/v1"]

# The single canonical string operators write at the top of every
# agent.yaml. Mirrors the literal so producers and consumers point
# at the same identifier without re-typing the string.
CURRENT_API_VERSION: ApiVersionV1 = "agentevaluator/v1"

# Frozen-set membership is the cheap "is this string a recognized
# version?" check the loader runs before dispatching to a version-
# specific parser. New versions are added here AND get their own
# ApiVersionV{N} literal above; the discriminated union in schema.py
# composes those literals into the public AgentManifest type.
SUPPORTED_API_VERSIONS: frozenset[str] = frozenset(
    {CURRENT_API_VERSION}
)


# The exact YAML key clients write at the top of every manifest.
# Hard-coded here (not derived from the field name on the model)
# because the loader inspects the raw mapping BEFORE Pydantic
# resolves the schema, so it needs the literal string by itself.
API_VERSION_KEY = "apiVersion"


__all__ = [
    "API_VERSION_KEY",
    "CURRENT_API_VERSION",
    "SUPPORTED_API_VERSIONS",
    "ApiVersionV1",
]
