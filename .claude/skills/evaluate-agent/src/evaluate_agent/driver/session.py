"""
Playwright browser session for driving a live web agent.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import (
    Page,
    async_playwright,
)

from evaluate_agent.manifest.schema import WebAccess

from .auth import context_kwargs_for


@asynccontextmanager
async def open_session(
    access: WebAccess,
    headless: bool = True,
) -> AsyncIterator[Page]:
    context_kwargs = context_kwargs_for(access)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless
        )
        try:
            context = await browser.new_context(
                **context_kwargs
            )
            try:
                page = await context.new_page()
                await page.goto(str(access.url))
                yield page
            finally:
                await context.close()
        finally:
            await browser.close()


__all__ = ["open_session"]
