"""
Agent manifest: schema, loader, discovery, and typed errors.
"""

from evaluate_agent.common.errors.manifest import (
    ManifestDiscoveryRootError,
    ManifestError,
    ManifestMissingApiVersionError,
    ManifestNotFoundError,
    ManifestSyntaxError,
    ManifestUnsupportedApiVersionError,
    ManifestValidationError,
)

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
    InteractionConfig,
    Precondition,
    UIExposedEvidence,
    UIIntrospectionSource,
)

__all__ = [
    "AgentManifest",
    "AgentManifestV1",
    "CURRENT_API_VERSION",
    "DiscoveredManifest",
    "DiscoveryFailure",
    "DiscoveryOutcome",
    "InteractionConfig",
    "ManifestDiscoveryRootError",
    "ManifestError",
    "ManifestMissingApiVersionError",
    "ManifestNotFoundError",
    "ManifestSyntaxError",
    "ManifestUnsupportedApiVersionError",
    "ManifestValidationError",
    "Precondition",
    "SUPPORTED_API_VERSIONS",
    "UIExposedEvidence",
    "UIIntrospectionSource",
    "discover_manifests",
    "load_manifest",
]
