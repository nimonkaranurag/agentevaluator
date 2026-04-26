"""
Record labeled page screenshots to the run artifact layout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from evaluate_agent.artifact_layout import RunArtifactLayout


class Screenshotable(Protocol):
    async def screenshot(
        self, *, path: str
    ) -> bytes | None: ...


_LABEL_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


class InvalidScreenshotLabel(ValueError):
    def __init__(self, label: str) -> None:
        self.label = label
        super().__init__(
            f"Screenshot label {label!r} is not a valid slug.\n"
            f"To proceed: pass a lowercase, letter-led label using only [a-z0-9_-] "
            f"(e.g. 'landing', 'after_submit', 'final_state'). Labels become part of the "
            f"screenshot filename so they must be filesystem-safe."
        )


@dataclass
class Screenshotter:
    layout: RunArtifactLayout
    case_id: str
    _step: int = field(default=0, init=False, repr=False)

    async def screenshot(
        self,
        page: Screenshotable,
        label: str,
    ) -> Path:
        if not _LABEL_RE.match(label):
            raise InvalidScreenshotLabel(label)
        self._step += 1
        path = self.layout.screenshot_path(
            self.case_id, self._step, label
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path))
        return path


__all__ = [
    "InvalidScreenshotLabel",
    "Screenshotable",
    "Screenshotter",
]
