"""
Free-form text type that rejects C0 control characters except tab and newline.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator

# C0 control characters span U+0000 through U+001F. Two members of
# that range are routinely needed in legitimate manifest text:
# tab (U+0009) appears in indented block scalars, newline (U+000A)
# is the line separator inside YAML folded/literal blocks. Every
# other codepoint in the range is rejected. NUL (U+0000) would
# truncate any C-string the manifest text reaches; ESC (U+001B)
# introduces ANSI sequences that smuggle styling and cursor
# moves into the rendered Markdown report; the rest are similarly
# unprintable and have no legitimate use in human-authored text.
_FORBIDDEN_CONTROL_CODEPOINTS = frozenset(
    set(range(0x00, 0x20)) - {0x09, 0x0A}
)


def _reject_control_characters(text: str) -> str:
    # Walk every character once and surface the first offender
    # with its index — a one-shot diagnostic the user can feed
    # straight into a hex editor or sed expression.
    for index, character in enumerate(text):
        if ord(character) in _FORBIDDEN_CONTROL_CODEPOINTS:
            raise ValueError(
                f"forbidden control character "
                f"U+{ord(character):04X} at index "
                f"{index}. Free-form manifest text must "
                f"not contain C0 control codepoints "
                f"(0x00–0x1F) other than tab (0x09) "
                f"and newline (0x0A) — the rest smuggle "
                f"ANSI escapes / NULs into the rendered "
                f"Markdown report. Strip the byte and "
                f"re-validate."
            )
    return text


# AfterValidator runs after the type-check and any other
# Annotated metadata pydantic resolves. Charset enforcement is
# orthogonal to length / pattern constraints, so SafeText layers
# cleanly on top of fields that also declare min_length /
# max_length via Field().
SafeText = Annotated[
    str,
    AfterValidator(_reject_control_characters),
]


__all__ = ["SafeText"]
