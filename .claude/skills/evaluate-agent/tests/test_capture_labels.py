"""
Tests pinning the capture-label contract that the driver writes and the scorer reads.
"""

from __future__ import annotations

from evaluate_agent.capture_labels import (
    LANDING_LABEL,
    POST_SUBMIT_LABEL,
)


class TestCaptureLabels:
    def test_landing_label_value(self):
        assert LANDING_LABEL == "landing"

    def test_post_submit_label_value(self):
        assert POST_SUBMIT_LABEL == "after_submit"

    def test_labels_distinct(self):
        assert LANDING_LABEL != POST_SUBMIT_LABEL
