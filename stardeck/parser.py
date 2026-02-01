"""Markdown parser for StarDeck."""

import re
from pathlib import Path

import yaml
from markdown_it import MarkdownIt

from stardeck.models import Deck, DeckConfig, SlideInfo


def _is_slide_delimiter(line: str) -> bool:
    """Check if line is a slide delimiter (--- at start of line)."""
    return bool(re.match(r"^---\s*$", line))


def _extract_frontmatter_lines(lines: list[str]) -> int:
    """Extract frontmatter block from start of file.

    Returns the index of the line after the closing ---.
    If no valid frontmatter, returns 0.
    """
    if not lines or lines[0].strip() != "---":
        return 0

    # Find the closing ---
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return i + 1

    return 0  # No closing --- found


def _process_lines_into_slides(
    lines: list[str],
    start_idx: int,
    initial_lines: list[str],
    initial_start: int,
) -> list[tuple[str, int, int]]:
    """Process lines into slide tuples starting from given index."""
    slides: list[tuple[str, int, int]] = []
    current_lines = initial_lines.copy()
    start_line = initial_start

    for i, line in enumerate(lines[start_idx:], start=start_idx):
        if _is_slide_delimiter(line):
            # Save current slide
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


def split_slides(content: str) -> list[tuple[str, int, int]]:
    """Split markdown content into slides by --- delimiter.

    Returns list of (content, start_line, end_line) tuples.
    Only splits on --- that appears at the start of a line.

    If the file starts with ---, the first --- and content up to the next ---
    is treated as frontmatter for the first slide (not a delimiter).
    """
    lines = content.split("\n")

    # Handle frontmatter at start of file
    frontmatter_end = _extract_frontmatter_lines(lines)
    if frontmatter_end > 0:
        # Include frontmatter in first slide
        initial_lines = lines[:frontmatter_end]
        return _process_lines_into_slides(lines, frontmatter_end, initial_lines, 0)

    # No frontmatter - process from beginning
    return _process_lines_into_slides(lines, 0, [], 0)


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from slide content.

    Returns (frontmatter_dict, remaining_content).
    If no frontmatter, returns ({}, original_content).
    """
    # Check if content starts with ---
    if not raw.startswith("---"):
        return {}, raw

    # Find the closing ---
    lines = raw.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        # No closing ---, treat as no frontmatter
        return {}, raw

    # Extract YAML content
    yaml_content = "\n".join(lines[1:end_idx])
    remaining = "\n".join(lines[end_idx + 1 :])

    # Parse YAML
    if yaml_content.strip():
        try:
            frontmatter = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError:
            frontmatter = {}
    else:
        frontmatter = {}

    return frontmatter, remaining


def extract_notes(content: str) -> tuple[str, str]:
    """Extract speaker notes from HTML comments.

    Looks for <!-- notes ... --> blocks and extracts the content.
    Returns (content_without_notes, notes_text).
    """
    # Pattern to match <!-- notes ... --> blocks
    pattern = r"<!--\s*notes\s*\n(.*?)-->"

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return content, ""

    # Extract notes content
    notes = match.group(1).strip()

    # Remove the notes block from content
    result = re.sub(pattern, "", content, flags=re.DOTALL).strip()

    return result, notes


def parse_deck(filepath: Path) -> Deck:
    """Parse a markdown file into a Deck.

    Combines split_slides, parse_frontmatter, extract_notes,
    and markdown-it-py rendering.
    """
    raw_content = filepath.read_text()
    md = MarkdownIt()

    # Split into raw slides
    raw_slides = split_slides(raw_content)

    slides: list[SlideInfo] = []
    for idx, (raw, start_line, end_line) in enumerate(raw_slides):
        # Extract frontmatter
        frontmatter, content = parse_frontmatter(raw)

        # Extract notes
        content, note = extract_notes(content)

        # Render markdown to HTML
        html_content = md.render(content)

        slide = SlideInfo(
            content=html_content,
            raw=raw,
            index=idx,
            start_line=start_line,
            end_line=end_line,
            frontmatter=frontmatter,
            note=note,
        )
        slides.append(slide)

    return Deck(
        slides=slides,
        config=DeckConfig(),
        filepath=filepath,
        raw=raw_content,
    )
