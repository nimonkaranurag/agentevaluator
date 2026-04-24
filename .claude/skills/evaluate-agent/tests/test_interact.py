"""
Unit tests for submit_case_input resolution, sequencing, and errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from evaluate_agent.driver.interact import (
    InputElementNotFound,
    submit_case_input,
)


@dataclass
class FakeLocator:
    selector: str
    matches: int
    fill_calls: list[str] = field(default_factory=list)
    press_calls: list[str] = field(default_factory=list)

    @property
    def first(self) -> "FakeLocator":
        return self

    async def count(self) -> int:
        return self.matches

    async def fill(self, value: str) -> None:
        self.fill_calls.append(value)

    async def press(self, key: str) -> None:
        self.press_calls.append(key)


@dataclass
class FakePage:
    locators: dict[str, FakeLocator] = field(
        default_factory=dict
    )
    timeouts: list[float] = field(default_factory=list)

    def locator(self, selector: str) -> FakeLocator:
        if selector not in self.locators:
            self.locators[selector] = FakeLocator(
                selector=selector, matches=0
            )
        return self.locators[selector]

    async def wait_for_timeout(
        self, timeout: float
    ) -> None:
        self.timeouts.append(timeout)


def _page_with(
    **selector_to_matches: int,
) -> FakePage:
    page = FakePage()
    for sel, n in selector_to_matches.items():
        page.locators[sel] = FakeLocator(
            selector=sel, matches=n
        )
    return page


class TestHintResolution:
    async def test_hint_wins_over_heuristic(
        self,
    ) -> None:
        page = _page_with()
        page.locators["#chat-input"] = FakeLocator(
            "#chat-input", 1
        )
        page.locators["textarea:visible"] = FakeLocator(
            "textarea:visible", 1
        )

        selector = await submit_case_input(
            page,
            "hello",
            input_selector="#chat-input",
        )

        assert selector == "#chat-input"
        assert page.locators["#chat-input"].fill_calls == [
            "hello"
        ]
        assert (
            page.locators["textarea:visible"].fill_calls
            == []
        )

    async def test_hint_zero_match_raises_with_hint_metadata(
        self,
    ) -> None:
        page = FakePage()

        with pytest.raises(InputElementNotFound) as excinfo:
            await submit_case_input(
                page,
                "hi",
                input_selector="#missing",
            )

        assert excinfo.value.hint == "#missing"
        assert excinfo.value.heuristic_selectors == ()
        text = str(excinfo.value)
        assert "'#missing'" in text
        assert "interaction.input_selector" in text
        assert "To proceed" in text


class TestHeuristicFallback:
    async def test_prefers_textarea(self) -> None:
        page = _page_with(
            **{
                "textarea:visible": 1,
                "input[type='text']:visible": 1,
            }
        )

        selector = await submit_case_input(page, "hi")

        assert selector == "textarea:visible"

    async def test_falls_through_to_text_input(
        self,
    ) -> None:
        page = _page_with(
            **{"input[type='text']:visible": 1}
        )

        selector = await submit_case_input(page, "hi")

        assert selector == "input[type='text']:visible"

    async def test_no_match_raises_with_heuristics_listed(
        self,
    ) -> None:
        page = FakePage()

        with pytest.raises(InputElementNotFound) as excinfo:
            await submit_case_input(page, "hi")

        assert excinfo.value.hint is None
        assert excinfo.value.heuristic_selectors == (
            "textarea:visible",
            "input[type='text']:visible",
        )
        text = str(excinfo.value)
        assert "'textarea:visible'" in text
        assert "\"input[type='text']:visible\"" in text
        assert "To proceed" in text


class TestSubmissionSequence:
    async def test_fill_then_press_enter_then_wait(
        self,
    ) -> None:
        page = _page_with(**{"textarea:visible": 1})

        await submit_case_input(
            page,
            "hello world",
            response_wait_ms=500,
        )

        target = page.locators["textarea:visible"]
        assert target.fill_calls == ["hello world"]
        assert target.press_calls == ["Enter"]
        assert page.timeouts == [500]

    async def test_default_wait_is_2000_ms(
        self,
    ) -> None:
        page = _page_with(**{"textarea:visible": 1})

        await submit_case_input(page, "hi")

        assert page.timeouts == [2000]

    async def test_hint_path_preserves_sequence(
        self,
    ) -> None:
        page = FakePage()
        page.locators["#x"] = FakeLocator("#x", 1)

        await submit_case_input(
            page,
            "probe",
            input_selector="#x",
            response_wait_ms=0,
        )

        assert page.locators["#x"].fill_calls == ["probe"]
        assert page.locators["#x"].press_calls == ["Enter"]
        assert page.timeouts == [0]
