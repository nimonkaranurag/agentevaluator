"""
Playwright driver for live-agent evaluation.
"""

from .auth import (
    MissingAuthEnvVar,
    context_kwargs_for,
)
from .auto_dom_snapshot import (
    AutoDOMSnapshotCollector,
    AutoDOMSnapshotCollectorAlreadyAttached,
    NavigatedFrame,
)
from .capture import (
    Capture,
    InvalidCaptureLabel,
    Screenshotable,
)
from .dom_snapshot import (
    DOMSnapshotable,
    DOMSnapshotter,
    InvalidDOMSnapshotLabel,
)
from .interact import (
    InputElementNotFound,
    submit_case_input,
)
from .session import Session, open_session
from .trace import (
    PageEventEmitter,
    TraceCollector,
    TraceCollectorAlreadyAttached,
    collect_trace,
)

__all__ = [
    "AutoDOMSnapshotCollector",
    "AutoDOMSnapshotCollectorAlreadyAttached",
    "Capture",
    "DOMSnapshotable",
    "DOMSnapshotter",
    "InputElementNotFound",
    "InvalidCaptureLabel",
    "InvalidDOMSnapshotLabel",
    "MissingAuthEnvVar",
    "NavigatedFrame",
    "PageEventEmitter",
    "Screenshotable",
    "Session",
    "TraceCollector",
    "TraceCollectorAlreadyAttached",
    "collect_trace",
    "context_kwargs_for",
    "open_session",
    "submit_case_input",
]
