"""
Extract user-visible text from a rendered DOM snapshot.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment

_NON_VISIBLE_TAGS = (
    "script",
    "style",
    "noscript",
    "template",
)
_WHITESPACE_RUN = re.compile(r"\s+")


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_NON_VISIBLE_TAGS):
        tag.decompose()
    for comment in soup.find_all(
        string=lambda node: isinstance(node, Comment)
    ):
        comment.extract()
    text = soup.get_text(separator=" ", strip=True)
    return _WHITESPACE_RUN.sub(" ", text).strip()


__all__ = ["extract_visible_text"]
