"""
Playwright driver for live-agent evaluation.
"""

from .artifact_layout import RunArtifactLayout
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
    TraceArtifactPaths,
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
    "RunArtifactLayout",
    "Screenshotable",
    "Session",
    "TraceArtifactPaths",
    "TraceCollector",
    "TraceCollectorAlreadyAttached",
    "collect_trace",
    "context_kwargs_for",
    "open_session",
    "submit_case_input",
]
