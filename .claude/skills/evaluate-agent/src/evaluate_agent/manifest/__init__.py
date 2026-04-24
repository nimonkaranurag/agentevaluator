"""
Agent manifest: schema, loader, discovery, and typed errors.
"""

from .discovery import (
    DiscoveredManifest,
    DiscoveryFailure,
    DiscoveryOutcome,
    discover_manifests,
)
from .errors import (
    ManifestDiscoveryRootError,
    ManifestError,
    ManifestNotFoundError,
    ManifestSyntaxError,
    ManifestValidationError,
)
from .loader import load_manifest
from .schema import AgentManifest, InteractionConfig

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
    "discover_manifests",
    "load_manifest",
]
