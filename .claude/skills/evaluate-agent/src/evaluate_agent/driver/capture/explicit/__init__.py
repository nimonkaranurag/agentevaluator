"""
Explicit single-shot evidence capture invoked by caller code.
"""

from .dom_snapshot import (
    DOMSnapshotable,
    DOMSnapshotter,
    InvalidDOMSnapshotLabel,
)
from .screenshot import (
    InvalidScreenshotLabel,
    Screenshotable,
    Screenshotter,
)

__all__ = [
    "DOMSnapshotable",
    "DOMSnapshotter",
    "InvalidDOMSnapshotLabel",
    "InvalidScreenshotLabel",
    "Screenshotable",
    "Screenshotter",
]
