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

from .artifact_layout import RunArtifactLayout
from .auth import context_kwargs_for
from .auto_dom_snapshot import AutoDOMSnapshotCollector
from .trace import (
    TraceArtifactPaths,
    collect_trace,
)


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
                    try:
                        await page.goto(str(access.url))
                        yield Session(
                            page=page,
                            trace_paths=trace_paths,
                        )
                    finally:
                        await auto_dom.flush()
                        auto_dom.detach(page)
                        collector.detach(page)
            finally:
                await context.close()
        finally:
            await browser.close()


__all__ = ["Session", "open_session"]
