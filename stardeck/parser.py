"""Markdown parser for StarDeck."""

import re


def split_slides(content: str) -> list[tuple[str, int, int]]:
    """Split markdown content into slides by --- delimiter.

    Returns list of (content, start_line, end_line) tuples.
    Only splits on --- that appears at the start of a line.
    """
    lines = content.split("\n")
    slides: list[tuple[str, int, int]] = []

    current_lines: list[str] = []
    start_line = 0

    for i, line in enumerate(lines):
        if line.strip() == "---" and re.match(r"^---\s*$", line):
            # Found delimiter - save current slide
            slide_content = "\n".join(current_lines)
            end_line = i - 1 if current_lines else i
            slides.append((slide_content, start_line, max(start_line, end_line)))

            # Start new slide
            current_lines = []
            start_line = i + 1
        else:
            current_lines.append(line)

    # Add final slide
    if current_lines or not slides:
        slide_content = "\n".join(current_lines)
        end_line = len(lines) - 1
        slides.append((slide_content, start_line, end_line))

    return slides
