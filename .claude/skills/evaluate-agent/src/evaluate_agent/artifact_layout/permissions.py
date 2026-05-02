"""
Owner-only directory permissions for captured run artifacts.
"""

from __future__ import annotations

from pathlib import Path

OWNER_ONLY_MODE = 0o700


def create_owner_only_dir(path: Path) -> None:
    if path.exists():
        path.chmod(OWNER_ONLY_MODE)
        return
    parent = path.parent
    if not parent.exists():
        create_owner_only_dir(parent)
    path.mkdir(mode=OWNER_ONLY_MODE)
    path.chmod(OWNER_ONLY_MODE)


__all__ = [
    "OWNER_ONLY_MODE",
    "create_owner_only_dir",
]
