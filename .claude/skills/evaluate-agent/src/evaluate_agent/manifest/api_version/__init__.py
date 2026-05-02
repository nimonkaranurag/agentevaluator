"""
Schema-versioning primitives: apiVersion literals and the supported registry.
"""

from .literal import (
    API_VERSION_KEY,
    CURRENT_API_VERSION,
    SUPPORTED_API_VERSIONS,
    ApiVersionV1,
)

__all__ = [
    "API_VERSION_KEY",
    "CURRENT_API_VERSION",
    "SUPPORTED_API_VERSIONS",
    "ApiVersionV1",
]
