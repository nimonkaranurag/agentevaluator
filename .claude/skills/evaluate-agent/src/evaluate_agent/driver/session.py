"""
Playwright browser session for driving a live web agent.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from evaluate_agent.manifest.schema import WebAccess
from playwright.async_api import (
    Page,
    async_playwright,
)

from ..artifact_layout import (
    RunArtifactLayout,
    TraceArtifactPaths,
)
from .auth import context_kwargs_for
from .capture import (
    AutoDOMSnapshotCollector,
    AutoScreenshotCollector,
    PageErrorDOMSnapshotCollector,
    PageErrorScreenshotCollector,
)
from .trace import collect_trace


@dataclass(frozen=True)
class Session:
    page: Page
    trace_paths: TraceArtifactPaths


@asynccontextmanager
async def open_session(
    access: WebAccess,
    layout: RunArtifactLayout,
    case_id: str,
    *,
    headless: bool = True,
) -> AsyncIterator[Session]:
    context_kwargs = context_kwargs_for(access)
    trace_paths = layout.trace_paths(case_id)
    trace_paths.ensure_dir()
    auto_dom = AutoDOMSnapshotCollector(
        layout=layout, case_id=case_id
    )
    auto_screenshot = AutoScreenshotCollector(
        layout=layout, case_id=case_id
    )
    page_error_dom = PageErrorDOMSnapshotCollector(
        layout=layout, case_id=case_id
    )
    page_error_screenshot = PageErrorScreenshotCollector(
        layout=layout, case_id=case_id
    )
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless
        )
        try:
            context = await browser.new_context(
                record_har_path=str(trace_paths.har_path),
                record_har_content="embed",
                **context_kwargs,
            )
            try:
                page = await context.new_page()
                async with collect_trace(
                    trace_paths
                ) as collector:
                    collector.attach(page)
                    auto_dom.attach(page)
                    auto_screenshot.attach(page)
                    page_error_dom.attach(page)
                    page_error_screenshot.attach(page)
                    try:
                        await page.goto(str(access.url))
                        yield Session(
                            page=page,
                            trace_paths=trace_paths,
                        )
                    finally:
                        await page_error_screenshot.flush()
                        await page_error_dom.flush()
                        await auto_screenshot.flush()
                        await auto_dom.flush()
                        page_error_screenshot.detach(page)
                        page_error_dom.detach(page)
                        auto_screenshot.detach(page)
                        auto_dom.detach(page)
                        collector.detach(page)
            finally:
                await context.close()
        finally:
            await browser.close()


__all__ = ["Session", "open_session"]
