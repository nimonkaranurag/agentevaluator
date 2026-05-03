"""
Agent manifest: schema, loader, discovery.
"""

from .api_version import (
    CURRENT_API_VERSION,
    SUPPORTED_API_VERSIONS,
)
from .discovery import (
    DiscoveredManifest,
    DiscoveryFailure,
    DiscoveryOutcome,
    discover_manifests,
)
from .loader import load_manifest
from .schema import (
    AgentManifest,
    AgentManifestV1,
    CallSpec,
    InteractionConfig,
    Precondition,
    UIExposedEvidence,
    UIIntrospectionSource,
)

__all__ = [
    "AgentManifest",
    "AgentManifestV1",
    "CURRENT_API_VERSION",
    "CallSpec",
    "DiscoveredManifest",
    "DiscoveryFailure",
    "DiscoveryOutcome",
    "InteractionConfig",
    "Precondition",
    "SUPPORTED_API_VERSIONS",
    "UIExposedEvidence",
    "UIIntrospectionSource",
    "discover_manifests",
    "load_manifest",
]
