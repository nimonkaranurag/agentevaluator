"""
Leaf constants for the manifest's apiVersion field, importable without triggering manifest package init.
"""

from __future__ import annotations

API_VERSION_KEY = "apiVersion"

CURRENT_API_VERSION = "agentevaluator/v1"

SUPPORTED_API_VERSIONS: frozenset[str] = frozenset(
    {CURRENT_API_VERSION}
)


__all__ = [
    "API_VERSION_KEY",
    "CURRENT_API_VERSION",
    "SUPPORTED_API_VERSIONS",
]
