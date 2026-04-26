"""
Event-triggered evidence capture subscribed to live page events.
"""

from .auto_dom_snapshot import (
    NAVIGATED_EVENT,
    NAVIGATED_EVENT_SUFFIX,
    AutoDOMSnapshotCollector,
    AutoDOMSnapshotCollectorAlreadyAttached,
    NavigatedFrame,
)
from .auto_screenshot import (
    AutoScreenshotCollector,
    AutoScreenshotCollectorAlreadyAttached,
)
from .collector_base import (
    EventTriggeredCaptureCollector,
    EventTriggeredCapturePage,
)
from .page_error_dom_snapshot import (
    PAGE_ERROR_EVENT,
    PAGE_ERROR_EVENT_SUFFIX,
    PageErrorDOMSnapshotCollector,
    PageErrorDOMSnapshotCollectorAlreadyAttached,
)
from .page_error_screenshot import (
    PageErrorScreenshotCollector,
    PageErrorScreenshotCollectorAlreadyAttached,
)

__all__ = [
    "AutoDOMSnapshotCollector",
    "AutoDOMSnapshotCollectorAlreadyAttached",
    "AutoScreenshotCollector",
    "AutoScreenshotCollectorAlreadyAttached",
    "EventTriggeredCaptureCollector",
    "EventTriggeredCapturePage",
    "NAVIGATED_EVENT",
    "NAVIGATED_EVENT_SUFFIX",
    "NavigatedFrame",
    "PAGE_ERROR_EVENT",
    "PAGE_ERROR_EVENT_SUFFIX",
    "PageErrorDOMSnapshotCollector",
    "PageErrorDOMSnapshotCollectorAlreadyAttached",
    "PageErrorScreenshotCollector",
    "PageErrorScreenshotCollectorAlreadyAttached",
]
