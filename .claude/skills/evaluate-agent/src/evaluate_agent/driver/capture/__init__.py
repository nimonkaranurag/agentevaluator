"""
Snapshot-style evidence capture for the live driver session.
"""

from .event_triggered import (
    NAVIGATED_EVENT,
    NAVIGATED_EVENT_SUFFIX,
    PAGE_ERROR_EVENT,
    PAGE_ERROR_EVENT_SUFFIX,
    AutoDOMSnapshotCollector,
    AutoDOMSnapshotCollectorAlreadyAttached,
    AutoScreenshotCollector,
    AutoScreenshotCollectorAlreadyAttached,
    EventTriggeredCaptureCollector,
    EventTriggeredCapturePage,
    NavigatedFrame,
    PageErrorDOMSnapshotCollector,
    PageErrorDOMSnapshotCollectorAlreadyAttached,
    PageErrorScreenshotCollector,
    PageErrorScreenshotCollectorAlreadyAttached,
)
from .explicit import (
    DOMSnapshotable,
    DOMSnapshotter,
    InvalidDOMSnapshotLabel,
    InvalidScreenshotLabel,
    Screenshotable,
    Screenshotter,
)

__all__ = [
    "AutoDOMSnapshotCollector",
    "AutoDOMSnapshotCollectorAlreadyAttached",
    "AutoScreenshotCollector",
    "AutoScreenshotCollectorAlreadyAttached",
    "DOMSnapshotable",
    "DOMSnapshotter",
    "EventTriggeredCaptureCollector",
    "EventTriggeredCapturePage",
    "InvalidDOMSnapshotLabel",
    "InvalidScreenshotLabel",
    "NAVIGATED_EVENT",
    "NAVIGATED_EVENT_SUFFIX",
    "NavigatedFrame",
    "PAGE_ERROR_EVENT",
    "PAGE_ERROR_EVENT_SUFFIX",
    "PageErrorDOMSnapshotCollector",
    "PageErrorDOMSnapshotCollectorAlreadyAttached",
    "PageErrorScreenshotCollector",
    "PageErrorScreenshotCollectorAlreadyAttached",
    "Screenshotable",
    "Screenshotter",
]
