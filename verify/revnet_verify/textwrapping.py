import re
import textwrap


PARAGRAPH_BREAK_PATTERN = re.compile(r'\n(?:[^\S\n]*\n)+')


def wrap_text(text: str, width: int, **kwargs) -> str:
    return '\n\n'.join(
        textwrap.fill(paragraph, width=width, **kwargs) for paragraph in PARAGRAPH_BREAK_PATTERN.split(text)
    )
