"""
Agent manifest: schema, loader, discovery, and typed errors.
"""

from evaluate_agent.common.errors.manifest import (
    ManifestDiscoveryRootError,
    ManifestError,
    ManifestNotFoundError,
    ManifestSyntaxError,
    ManifestValidationError,
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
    InteractionConfig,
    Precondition,
    UIExposedEvidence,
    UIIntrospectionSource,
)

__all__ = [
    "AgentManifest",
    "DiscoveredManifest",
    "DiscoveryFailure",
    "DiscoveryOutcome",
    "InteractionConfig",
    "ManifestDiscoveryRootError",
    "ManifestError",
    "ManifestNotFoundError",
    "ManifestSyntaxError",
    "ManifestValidationError",
    "Precondition",
    "UIExposedEvidence",
    "UIIntrospectionSource",
    "discover_manifests",
    "load_manifest",
]
