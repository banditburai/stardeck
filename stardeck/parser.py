"""Markdown parser for StarDeck."""

import re
from pathlib import Path

import yaml
from markdown_it import MarkdownIt

from stardeck.models import Deck, DeckConfig, SlideInfo


def _is_slide_delimiter(line: str) -> bool:
    """Check if line is a slide delimiter (--- at start of line)."""
    return bool(re.match(r"^---\s*$", line))


def _is_yaml_like(text: str) -> bool:
    """Check if text looks like YAML frontmatter (key: value pairs only)."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return False
    # Check if all non-empty lines look like YAML key: value
    for line in lines:
        if not re.match(r"^[\w_-]+:\s*.+$", line):
            return False
    return True


def _find_frontmatter_end(lines: list[str], start: int) -> int:
    """Find the closing --- of a frontmatter block.

    Returns the index of the closing ---, or -1 if not found.
    """
    for i, line in enumerate(lines[start:], start=start):
        if _is_slide_delimiter(line):
            return i
    return -1


def split_slides(content: str) -> list[tuple[str, int, int]]:
    """Split markdown content into slides by --- delimiter.

    Returns list of (content, start_line, end_line) tuples.

    Handles Slidev-style frontmatter for mid-deck slides:
    ---
    layout: cover
    ---
    # Content

    The above is ONE slide with frontmatter, not two slides.
    """
    lines = content.split("\n")
    slides: list[tuple[str, int, int]] = []

    i = 0
    current_lines: list[str] = []
    start_line = 0

    while i < len(lines):
        line = lines[i]

        if _is_slide_delimiter(line):
            # Check if this starts a frontmatter block
            # Look ahead to see if there's YAML followed by another ---
            fm_end = _find_frontmatter_end(lines, i + 1)

            if fm_end > i + 1:
                # There's content between this --- and the next ---
                potential_yaml = "\n".join(lines[i + 1 : fm_end])

                if _is_yaml_like(potential_yaml):
                    # This is slide frontmatter, not a separate slide
                    # Save current slide first
                    if current_lines or slides:
                        slide_content = "\n".join(current_lines)
                        end_line = i - 1 if current_lines else i
                        slides.append((slide_content, start_line, max(start_line, end_line)))

                    # Start new slide with frontmatter included
                    current_lines = lines[i : fm_end + 1]  # Include ---, yaml, ---
                    start_line = i
                    i = fm_end + 1
                    continue

            # Regular slide delimiter (no frontmatter follows)
            if current_lines or slides:
                slide_content = "\n".join(current_lines)
                end_line = i - 1 if current_lines else i
                slides.append((slide_content, start_line, max(start_line, end_line)))

            current_lines = []
            start_line = i + 1
        else:
            current_lines.append(line)

        i += 1

    # Add final slide
    if current_lines or not slides:
        slide_content = "\n".join(current_lines)
        end_line = len(lines) - 1
        slides.append((slide_content, start_line, end_line))

    return slides


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


def count_click_tags(content: str) -> int:
    """Count the number of <click> tags in content."""
    return len(re.findall(r"<click[^>]*>", content, re.IGNORECASE))


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


def _create_markdown_renderer() -> MarkdownIt:
    """Create a MarkdownIt instance with Pygments syntax highlighting."""
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.lexers.special import TextLexer

    md = MarkdownIt().enable("table")

    # Override the fence renderer to use Pygments
    def render_fence(self, tokens, idx, options, env):
        token = tokens[idx]
        code = token.content.rstrip("\n")
        lang = token.info.strip() if token.info else ""

        try:
            lexer = get_lexer_by_name(lang) if lang else TextLexer()
        except Exception:
            lexer = TextLexer()

        formatter = HtmlFormatter(nowrap=True)
        highlighted = highlight(code, lexer, formatter)
        return f'<pre><code class="language-{lang}">{highlighted}</code></pre>\n'

    md.add_render_rule("fence", render_fence)
    return md


def parse_deck(filepath: Path) -> Deck:
    """Parse a markdown file into a Deck.

    Combines split_slides, parse_frontmatter, extract_notes,
    and markdown-it-py rendering.
    """
    raw_content = filepath.read_text()
    md = _create_markdown_renderer()

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
