"""
ApiVersion literal type alias bound to the canonical string in common.manifest_constants.
"""

from __future__ import annotations

from typing import Literal

from evaluate_agent.common.manifest_constants import (
    API_VERSION_KEY,
    CURRENT_API_VERSION,
    SUPPORTED_API_VERSIONS,
)

# Per-version literal type. The pattern is one literal alias per
# version (ApiVersionV1 today, ApiVersionV2 when v2 ships) so that
# every versioned AgentManifest model can pin its apiVersion field
# to its own literal — making the union of versioned models a true
# discriminated union once a second variant exists. Literal type
# parameters must be string literals, so the canonical string from
# common.manifest_constants is duplicated here at the type level.
ApiVersionV1 = Literal["agentevaluator/v1"]


__all__ = [
    "API_VERSION_KEY",
    "CURRENT_API_VERSION",
    "SUPPORTED_API_VERSIONS",
    "ApiVersionV1",
]
