"""Markdown parser for StarDeck."""

import re
from pathlib import Path

import yaml
from markdown_it import MarkdownIt

from stardeck.models import Deck, DeckConfig, SlideInfo

_YAML_KEY_RE = re.compile(r"^[\w-]+:\s*")
_NOTES_RE = re.compile(r"<!--\s*notes\s*\n(.*?)-->", re.DOTALL)
_REGION_TAGS = ("bottom", "item", "left", "main", "right", "sidebar", "step", "top")
_REGION_RE = re.compile(
    r"<(" + "|".join(_REGION_TAGS) + r")(\s[^>]*)?>(.+?)</\1>",
    re.DOTALL,
)


def _is_slide_delimiter(line: str) -> bool:
    return line.rstrip() == "---"


def _is_yaml_like(text: str) -> bool:
    """Lightweight heuristic — avoids YAML parsing at split time."""
    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
    return bool(lines) and all(_YAML_KEY_RE.match(ln) for ln in lines)


def _find_frontmatter_end(lines: list[str], start: int) -> int:
    for i in range(start, len(lines)):
        if _is_slide_delimiter(lines[i]):
            return i
    return -1


def split_slides(content: str) -> list[str]:
    """Split markdown content into slides by --- delimiter.

    Handles Slidev-style mid-deck frontmatter: a --- / YAML / --- block
    is attached to the following slide, not treated as a separate delimiter.
    """
    lines = content.split("\n")
    slides: list[str] = []
    current: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if _is_slide_delimiter(line):
            fm_end = _find_frontmatter_end(lines, i + 1)
            if fm_end > i + 1 and _is_yaml_like("\n".join(lines[i + 1 : fm_end])):
                if current or slides:
                    slides.append("\n".join(current))
                current = lines[i : fm_end + 1]
                i = fm_end + 1
                continue

            if current or slides:
                slides.append("\n".join(current))
            current = []
        else:
            current.append(line)
        i += 1

    if current or not slides:
        slides.append("\n".join(current))
    return slides


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from slide content.

    Returns (frontmatter_dict, remaining_content).
    """
    if not raw.startswith("---"):
        return {}, raw

    lines = raw.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, raw

    yaml_content = "\n".join(lines[1:end_idx])
    remaining = "\n".join(lines[end_idx + 1 :])

    try:
        frontmatter = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, remaining


def transform_click_tags(content: str) -> tuple[str, int]:
    """Transform <click>...</click> to click-reveal divs.

    Returns (transformed_content, max_clicks).
    """
    matches = list(re.finditer(r"<click>(.*?)</click>", content, re.DOTALL))
    if not matches:
        return content, 0

    parts = []
    last_end = 0
    for i, match in enumerate(matches, 1):
        parts.append(content[last_end : match.start()])
        parts.append(
            f'<div class="click-reveal" data-click="{i}" data-class:revealed="$clicks >= {i}">{match.group(1)}</div>'
        )
        last_end = match.end()
    parts.append(content[last_end:])

    return "".join(parts), len(matches)


def transform_regions(content: str) -> str:
    """Transform region tags (<left>...</left>) into div wrappers.

    Skips content inside code fences.
    """
    fences: list[str] = []

    def _stash_fence(m: re.Match) -> str:
        fences.append(m.group(0))
        return f"\x00FENCE{len(fences) - 1}\x00"

    protected = re.sub(r"```.*?```", _stash_fence, content, flags=re.DOTALL)

    def _replace_region(m: re.Match) -> str:
        tag, attrs, inner = m.group(1), m.group(2) or "", m.group(3).strip()
        cls_match = re.search(r'class="([^"]*)"', attrs) if attrs else None
        extra = cls_match.group(1) if cls_match else ""
        cls = f"sd-region {extra}".strip() if extra else "sd-region"
        return f'\n<div class="{cls}" data-region="{tag}">\n\n{inner}\n\n</div>\n'

    result = _REGION_RE.sub(_replace_region, protected)

    for i, fence in enumerate(fences):
        result = result.replace(f"\x00FENCE{i}\x00", fence)
    return result


def extract_notes(content: str) -> tuple[str, str]:
    """Extract <!-- notes ... --> blocks. Handles multiple note blocks per slide."""
    matches = list(_NOTES_RE.finditer(content))
    if not matches:
        return content, ""

    notes = "\n\n".join(m.group(1).strip() for m in matches)
    parts, last = [], 0
    for m in matches:
        parts.append(content[last : m.start()])
        last = m.end()
    parts.append(content[last:])
    return "".join(parts).strip(), notes


def _create_markdown_renderer() -> MarkdownIt:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.lexers.special import TextLexer

    md = MarkdownIt().enable("table")
    formatter = HtmlFormatter(nowrap=True)

    def render_fence(self, tokens, idx, options, env):
        token = tokens[idx]
        code = token.content.rstrip("\n")
        lang = token.info.strip() if token.info else ""
        try:
            lexer = get_lexer_by_name(lang) if lang else TextLexer()
        except Exception:
            lexer = TextLexer()
        highlighted = highlight(code, lexer, formatter)
        return f'<pre><code class="language-{lang}">{highlighted}</code></pre>\n'

    md.add_render_rule("fence", render_fence)

    # cls= → class= in raw HTML (StarHTML convention)
    def _cls_to_class(self, tokens, idx, options, env):
        return re.sub(r"(?<=\s)cls=", "class=", tokens[idx].content)

    md.add_render_rule("html_block", _cls_to_class)
    md.add_render_rule("html_inline", _cls_to_class)
    return md


def parse_deck(filepath: Path) -> Deck:
    raw_content = filepath.read_text()
    md = _create_markdown_renderer()

    slides: list[SlideInfo] = []
    for idx, raw in enumerate(split_slides(raw_content)):
        frontmatter, content = parse_frontmatter(raw)
        content, note = extract_notes(content)
        content = transform_regions(content)
        content, max_clicks = transform_click_tags(content)

        slides.append(
            SlideInfo(
                content=md.render(content),
                index=idx,
                frontmatter=frontmatter,
                note=note,
                max_clicks=max_clicks,
            )
        )

    deck_fm = slides[0].frontmatter if slides else {}
    config_fields = {k: deck_fm[k] for k in ("title", "transition") if k in deck_fm and deck_fm[k]}
    return Deck(slides=slides, config=DeckConfig(**config_fields))
