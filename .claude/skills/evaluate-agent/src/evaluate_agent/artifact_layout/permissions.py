"""
Owner-only directory permissions for captured run artifacts.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

OWNER_ONLY_MODE = 0o700

# Mask out every group/other bit at directory creation time. The
# pair (mode=0o700, umask=0o077) is redundant on Linux/macOS — the
# kernel produces 0o700 from either alone — but on platforms
# where Path.mkdir's mode argument is silently ignored, the
# umask is what makes the new directory owner-only at the
# instant it appears in the namespace. The chmod that previously
# followed mkdir was a defense for that ignored-mode case but
# left a TOCTOU window between the two syscalls during which
# another process could observe the directory at the platform
# default mode. Setting the umask first closes the window.
_OWNER_ONLY_UMASK = 0o077


@contextmanager
def _restrictive_umask() -> Iterator[None]:
    # os.umask is process-global. Holding it inside a tight
    # scope minimises the window during which a sibling thread
    # could create files under the more restrictive mask. In
    # this codebase directory creation is not concurrent with
    # other umask-sensitive work, so the global mutation is
    # acceptable; the restore in finally ensures we never leak
    # the more restrictive mask to unrelated callers.
    prior = os.umask(_OWNER_ONLY_UMASK)
    try:
        yield
    finally:
        os.umask(prior)


def create_owner_only_dir(path: Path) -> None:
    if path.exists():
        # The path exists from a prior run or external setup.
        # Re-asserting 0o700 here keeps the contract regardless
        # of the prior creator's umask. Symlinked directories
        # are intentionally left alone — chmod through a
        # symlink would mutate the target's mode, and chmod
        # already follows symlinks; if a caller hands us a
        # symlink they should know what they're pointing at.
        path.chmod(OWNER_ONLY_MODE)
        return
    parent = path.parent
    if not parent.exists():
        # Recurse before mkdir so the parent is also locked
        # down. Without this, intermediate directories would be
        # created under whatever the inherited umask provides —
        # often 0o755 — and a captured artifact in a deeply
        # nested case_dir would be reachable through a
        # world-readable parent even though the leaf is 0o700.
        create_owner_only_dir(parent)
    with _restrictive_umask():
        # mkdir under the restrictive umask creates the
        # directory at 0o700 atomically — no second syscall is
        # needed to lower the mode, so no window exists where
        # another process could observe a more permissive
        # state.
        path.mkdir(mode=OWNER_ONLY_MODE)


__all__ = [
    "OWNER_ONLY_MODE",
    "create_owner_only_dir",
]
