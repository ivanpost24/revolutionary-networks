"""Utility module for wrapping text with multiple paragraphs."""

import re
import textwrap


PARAGRAPH_BREAK_PATTERN = re.compile(r'\n(?:[^\S\n]*\n)+')


def wrap_text(text: str, width: int, **kwargs) -> str:
    """
    Wrap the provided multi-paragraph text into the given width. This is a wrapper for multiple textwrap.fill() calls.
    Paragraphs are separated by at least two newline characters.
    """
    return '\n\n'.join(
        textwrap.fill(paragraph, width=width, **kwargs) for paragraph in PARAGRAPH_BREAK_PATTERN.split(text)
    )
