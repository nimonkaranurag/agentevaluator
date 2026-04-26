"""
Tests for the PageErrorEntry on-disk schema.
"""

from __future__ import annotations

import pytest
from evaluate_agent.scoring import PageErrorEntry
from pydantic import ValidationError


class TestRequiredFields:
    def test_happy_path(self):
        entry = PageErrorEntry(
            ts="2026-04-26T12:00:00.000+00:00",
            message="ReferenceError: x is not defined",
        )
        assert entry.ts == ("2026-04-26T12:00:00.000+00:00")
        assert entry.message.startswith("ReferenceError")

    def test_ts_required(self):
        with pytest.raises(ValidationError):
            PageErrorEntry(
                message="x"
            )  # type: ignore[call-arg]

    def test_message_required(self):
        with pytest.raises(ValidationError):
            PageErrorEntry(
                ts="2026-04-26T12:00:00.000+00:00"
            )  # type: ignore[call-arg]

    def test_ts_min_length(self):
        with pytest.raises(ValidationError):
            PageErrorEntry(ts="", message="x")

    def test_message_min_length(self):
        with pytest.raises(ValidationError):
            PageErrorEntry(
                ts="2026-04-26T12:00:00.000+00:00",
                message="",
            )


class TestStrictness:
    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            PageErrorEntry(
                ts="2026-04-26T12:00:00.000+00:00",
                message="x",
                stack="(unused)",  # type: ignore[call-arg]
            )

    def test_frozen(self):
        entry = PageErrorEntry(
            ts="2026-04-26T12:00:00.000+00:00",
            message="x",
        )
        with pytest.raises(ValidationError):
            entry.message = "different"  # type: ignore[misc]


class TestRoundTrip:
    def test_dump_then_validate_returns_equal_entry(self):
        original = PageErrorEntry(
            ts="2026-04-26T12:00:00.000+00:00",
            message="TypeError: undefined is not a function",
        )
        text = original.model_dump_json()
        reconstituted = PageErrorEntry.model_validate_json(
            text
        )
        assert reconstituted == original
