"""
Tests for visible-text extraction from rendered DOM.
"""

from __future__ import annotations

import pytest
from evaluate_agent.scoring.dom_text import (
    extract_visible_text,
)


class TestVisibleTags:
    def test_plain_paragraph(self):
        assert (
            extract_visible_text("<p>Hello there</p>")
            == "Hello there"
        )

    def test_block_elements_separated(self):
        text = extract_visible_text(
            "<div>Hello</div><div>there</div>"
        )
        assert text == "Hello there"

    def test_nested_inline(self):
        text = extract_visible_text(
            "<p>Hello <strong>brave</strong> "
            "<em>new</em> world</p>"
        )
        assert text == "Hello brave new world"


class TestNonVisibleTagsExcluded:
    @pytest.mark.parametrize(
        "tag",
        ["script", "style", "noscript", "template"],
    )
    def test_tag_excluded(self, tag):
        html = (
            f"<p>visible</p>"
            f"<{tag}>hidden_payload</{tag}>"
            f"<p>more visible</p>"
        )
        text = extract_visible_text(html)
        assert "hidden_payload" not in text
        assert "visible" in text
        assert "more visible" in text

    def test_inline_script_in_head_excluded(self):
        html = (
            "<html><head><script>"
            "alert('boo');"
            "</script></head><body>Body text"
            "</body></html>"
        )
        text = extract_visible_text(html)
        assert "alert" not in text
        assert text == "Body text"


class TestComments:
    def test_html_comment_excluded(self):
        text = extract_visible_text(
            "<p>Visible <!-- secret note --> "
            "still visible</p>"
        )
        assert "secret note" not in text
        assert "Visible" in text
        assert "still visible" in text

    def test_comment_only_returns_empty(self):
        text = extract_visible_text(
            "<!-- only a comment -->"
        )
        assert text == ""


class TestWhitespaceNormalization:
    def test_multi_space_collapsed(self):
        text = extract_visible_text(
            "<p>Hello     there</p>"
        )
        assert text == "Hello there"

    def test_newlines_collapsed(self):
        text = extract_visible_text(
            "<p>Hello\n\nthere\n\nfriend</p>"
        )
        assert text == "Hello there friend"

    def test_tabs_collapsed(self):
        text = extract_visible_text(
            "<p>Hello\t\t\tthere</p>"
        )
        assert text == "Hello there"

    def test_leading_trailing_stripped(self):
        text = extract_visible_text("  <p>  Hello  </p>  ")
        assert text == "Hello"


class TestUnicodeAndEdgeCases:
    def test_non_ascii_preserved(self):
        text = extract_visible_text(
            "<p>Olá, posso ajudá-lo?</p>"
        )
        assert text == "Olá, posso ajudá-lo?"

    def test_emoji_preserved(self):
        text = extract_visible_text(
            "<p>Booking confirmed ✅</p>"
        )
        assert text == "Booking confirmed ✅"

    def test_empty_string_returns_empty(self):
        assert extract_visible_text("") == ""

    def test_only_whitespace_returns_empty(self):
        assert (
            extract_visible_text("<p>   \n\t  </p>") == ""
        )

    def test_malformed_html_handled(self):
        text = extract_visible_text(
            "<div><p>Hello <b>brave</p>" "world<unclosed"
        )
        assert "Hello" in text
        assert "brave" in text


class TestRealisticAgentResponse:
    def test_chat_message_structure(self):
        html = """
        <html>
          <body>
            <div class="chat-log">
              <div class="message user">Hi there</div>
              <div class="message agent">
                Booking confirmed for JFK to LHR on
                Friday, 14 May 2026. Confirmation
                number: CRY3W4.
              </div>
            </div>
            <script>
              window.dataLayer.push({event: 'message'});
            </script>
          </body>
        </html>
        """
        text = extract_visible_text(html)
        assert "Hi there" in text
        assert "Booking confirmed for JFK to LHR" in text
        assert "Confirmation number: CRY3W4" in text
        assert "dataLayer" not in text
