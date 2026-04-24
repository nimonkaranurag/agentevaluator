"""
Submit a case's input into the agent's primary web input field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class _LocatorLike(Protocol):
    @property
    def first(self) -> "_LocatorLike": ...

    async def count(self) -> int: ...

    async def fill(self, value: str) -> None: ...

    async def press(self, key: str) -> None: ...


class _PageLike(Protocol):
    def locator(self, selector: str) -> _LocatorLike: ...

    async def wait_for_timeout(
        self, timeout: float
    ) -> None: ...


_HEURISTIC_SELECTORS: tuple[str, ...] = (
    "textarea:visible",
    "input[type='text']:visible",
)


def _describe_heuristics() -> str:
    return ", ".join(repr(s) for s in _HEURISTIC_SELECTORS)


class InputElementNotFound(RuntimeError):
    def __init__(
        self,
        *,
        hint: str | None,
        heuristic_selectors: tuple[str, ...],
    ) -> None:
        self.hint = hint
        self.heuristic_selectors = heuristic_selectors
        if hint is not None:
            message = (
                f"No element matched the manifest's declared interaction.input_selector {hint!r}.\n"
                f"To proceed:\n"
                f"  (1) Open the agent URL in a browser, inspect the primary input field, and copy a CSS selector that resolves to exactly that element on initial page load.\n"
                f"  (2) Replace interaction.input_selector in the manifest with the corrected selector (keep it quoted in YAML if it contains colons or quotes).\n"
                f"  (3) Re-run the invocation. If the corrected selector succeeds, the driver types case.input into it. If it still returns zero matches, remove interaction.input_selector from the manifest to fall back to heuristic resolution over {_describe_heuristics()}."
            )
        else:
            tried = ", ".join(
                repr(s) for s in heuristic_selectors
            )
            message = (
                f"The driver's heuristic input-field resolution found no match. Selectors tried in order: {tried}.\n"
                f"To proceed:\n"
                f"  (1) Open the agent URL in a browser, inspect the primary input field, and copy a CSS selector that resolves to exactly that element on initial page load.\n"
                f"  (2) Add interaction.input_selector to the manifest with the copied selector.\n"
                f"  (3) Re-run the invocation. A manifest-declared selector takes precedence over the heuristic. If your selector matches at least one element, the driver types case.input into it. If your selector returns zero matches, the driver raises InputElementNotFound with hint-branch recovery — re-inspect the page's rendered DOM (the input may live inside an iframe or a shadow root that CSS selectors cannot reach) and correct the selector."
            )
        super().__init__(message)


@dataclass(frozen=True)
class _ResolvedInput:
    selector: str
    locator: _LocatorLike


async def _resolve_input(
    page: _PageLike, hint: str | None
) -> _ResolvedInput:
    if hint is not None:
        located = page.locator(hint)
        if await located.count() > 0:
            return _ResolvedInput(
                selector=hint, locator=located.first
            )
        raise InputElementNotFound(
            hint=hint, heuristic_selectors=()
        )
    for candidate in _HEURISTIC_SELECTORS:
        located = page.locator(candidate)
        if await located.count() > 0:
            return _ResolvedInput(
                selector=candidate,
                locator=located.first,
            )
    raise InputElementNotFound(
        hint=None,
        heuristic_selectors=_HEURISTIC_SELECTORS,
    )


async def submit_case_input(
    page: _PageLike,
    case_input: str,
    *,
    input_selector: str | None = None,
    response_wait_ms: int = 2000,
) -> str:
    """
    Return the CSS selector used to locate the input field.
    """
    resolved = await _resolve_input(
        page=page, hint=input_selector
    )
    await resolved.locator.fill(case_input)
    await resolved.locator.press("Enter")
    await page.wait_for_timeout(response_wait_ms)
    return resolved.selector


__all__ = [
    "InputElementNotFound",
    "submit_case_input",
]
