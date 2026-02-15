"""Markdown parser for StarDeck."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from markdown_it import MarkdownIt
from starhtml import Signal
from starhtml.plugins import enter, exit_, visibility

from stardeck.models import Deck, DeckConfig, SlideInfo

_YAML_KEY_RE = re.compile(r"^[\w-]+:\s*")
_NOTES_RE = re.compile(r"<!--\s*notes\s*\n(.*?)-->", re.DOTALL)
_CLICK_RE = re.compile(
    r"<(click|after)(\s[^>]*)?>(.+?)</\1>",
    re.DOTALL,
)
_CLICKS_RE = re.compile(
    r"<clicks(\s[^>]*)?>(.+?)</clicks>",
    re.DOTALL,
)
_ATTR_RE = re.compile(r'([\w-]+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')
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
    """Extract YAML frontmatter from slide content."""
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


@dataclass
class ClickDefaults:
    animation: str = "fade"
    duration: int | None = None
    delay: int | None = None
    ease: str | None = None
    spring: str | None = None


@dataclass
class ClickResult:
    content: str
    max_clicks: int
    range_clicks: frozenset[tuple[int, int]] = field(default_factory=frozenset)


def _parse_click_attrs(tag_attrs: str) -> dict:
    attrs = {}
    for m in _ATTR_RE.finditer(tag_attrs):
        key = m.group(1)
        val = m.group(2) or m.group(3) or m.group(4) or ""
        attrs[key] = int(val) if val and val.lstrip("-").isdigit() else val
    return attrs


def _is_bare_attr(tag_attrs: str, name: str) -> bool:
    """Detect bare boolean attribute (e.g., 'hide' without '=value')."""
    stripped = _ATTR_RE.sub("", tag_attrs)
    return name in stripped.split()


_CODE_RE = re.compile(r"```.*?```|`[^`]+`", re.DOTALL)


def _stash_code(content: str) -> tuple[str, list[str]]:
    """Protect code blocks from click/region transforms."""
    stashed: list[str] = []

    def _replace(m: re.Match) -> str:
        stashed.append(m.group(0))
        return f"\x00CODE{len(stashed) - 1}\x00"

    return _CODE_RE.sub(_replace, content), stashed


def _restore_code(content: str, stashed: list[str]) -> str:
    for i, original in enumerate(stashed):
        content = content.replace(f"\x00CODE{i}\x00", original)
    return content


_TRANSFORM_PROPS = {"x", "y", "scale", "rotate", "opacity"}


def _build_enter_kwargs(attrs: dict, defaults: ClickDefaults) -> dict:
    kw: dict = {}
    kw["preset"] = attrs.get("animation", defaults.animation)
    duration = attrs.get("duration", defaults.duration)
    kw["duration"] = duration if duration is not None else 300
    kw["delay"] = attrs.get("delay", defaults.delay)
    kw["ease"] = attrs.get("ease", defaults.ease)
    kw["spring"] = attrs.get("spring", defaults.spring)
    overrides = _TRANSFORM_PROPS & attrs.keys()
    for prop in overrides:
        kw[prop] = attrs[prop]
    if overrides:
        kw.pop("preset", None)
    return {k: v for k, v in kw.items() if v is not None}


def _build_exit_kwargs(attrs: dict) -> dict:
    kw: dict = {}
    for prop in ("duration", "delay", "ease", "spring", "x", "y", "scale", "rotate", "opacity"):
        if (val := attrs.get(f"exit-{prop}")) is not None:
            kw[prop] = val
    return kw or {"opacity": 0, "duration": 250}


def transform_clicks_wrapper(content: str) -> str:
    """Expand <clicks> wrappers into individual <click> tags per paragraph."""
    content, stashed = _stash_code(content)

    def _expand(m: re.Match) -> str:
        attrs = m.group(1) or ""
        inner = m.group(2).strip()
        paragraphs = [p.strip() for p in re.split(r"\n\n+", inner) if p.strip()]
        return "\n\n".join(f"<click{attrs}>{p}</click>" for p in paragraphs)

    return _restore_code(_CLICKS_RE.sub(_expand, content), stashed)


def _resolve_click_number(tag_name, at_val, current_click):
    if at_val is not None:
        if isinstance(at_val, str) and "-" in at_val:
            lo, hi = (int(x) for x in at_val.split("-", 1))
            return 0, lo, hi, True, current_click
        return int(at_val), 0, 0, False, current_click

    if tag_name == "click":
        current_click += 1
    elif current_click == 0:
        current_click = 1
    return current_click, 0, 0, False, current_click


def _click_div(
    inner: str, data_click: str, *, hide: bool = False,
    sig_name: str, css_expr: str, attrs: dict, defaults: ClickDefaults,
    use_motion: bool,
) -> str:
    if hide:
        return (
            f'<div class="click-hide" data-click="{data_click}"'
            f' data-class:click-hidden="{css_expr}">'
            f"{inner}</div>"
        )
    if not use_motion:
        return (
            f'<div class="click-reveal" data-click="{data_click}"'
            f' data-class:revealed="{css_expr}">'
            f"{inner}</div>"
        )
    motion_str = visibility(
        signal=sig_name,
        enter=enter(**_build_enter_kwargs(attrs, defaults)),
        exit_=exit_(**_build_exit_kwargs(attrs)),
    )
    return (
        f'<div class="click-reveal" data-click="{data_click}"'
        f' data-motion="{motion_str}">'
        f"{inner}</div>"
    )


def _process_match(match, current_click, highest_click, range_clicks, defaults, use_motion):
    tag_attrs = match.group(2) or ""
    attrs = _parse_click_attrs(tag_attrs)
    hide = _is_bare_attr(tag_attrs, "hide")

    click_num, lo, hi, is_range, current_click = _resolve_click_number(
        match.group(1), attrs.get("at"), current_click,
    )
    if is_range:
        highest_click = max(highest_click, hi)
        range_clicks.add((lo, hi))
    elif attrs.get("at") is not None:
        highest_click = max(highest_click, click_num)

    if is_range:
        data_click, sig_name = f"{lo}-{hi}", f"vis_{lo}_{hi}"
        css_expr = f"$clicks >= {lo} && $clicks < {hi}"
    else:
        data_click, sig_name = str(click_num), f"vis{click_num}"
        css_expr = f"$clicks >= {click_num}"

    html = _click_div(
        match.group(3), data_click, hide=hide,
        sig_name=sig_name, css_expr=css_expr, attrs=attrs,
        defaults=defaults, use_motion=use_motion,
    )
    return html, click_num, hide, current_click, highest_click


def transform_click_tags(
    content: str,
    *,
    defaults: ClickDefaults | None = None,
    use_motion: bool = False,
) -> ClickResult:
    if defaults is None:
        defaults = ClickDefaults()

    content, stashed = _stash_code(content)
    matches = list(_CLICK_RE.finditer(content))
    if not matches:
        return ClickResult(_restore_code(content, stashed), 0)

    parts: list[str] = []
    last_end = 0
    current_click = 0
    highest_click = 0
    range_clicks: set[tuple[int, int]] = set()
    i = 0

    while i < len(matches):
        match = matches[i]
        parts.append(content[last_end:match.start()])

        html, click_num, hide, current_click, highest_click = _process_match(
            match, current_click, highest_click, range_clicks, defaults, use_motion,
        )

        # Detect hide+after pair: wrap in .click-swap so they crossfade in-place
        next_is_after = (
            hide
            and i + 1 < len(matches)
            and matches[i + 1].group(1) == "after"
        )
        if next_is_after:
            after_match = matches[i + 1]
            after_html, _, _, current_click, highest_click = _process_match(
                after_match, current_click, highest_click, range_clicks, defaults, use_motion,
            )
            parts.append(f'<div class="click-swap">{html}{after_html}</div>')
            last_end = after_match.end()
            i += 2
        else:
            parts.append(html)
            last_end = match.end()
            i += 1

    parts.append(content[last_end:])
    return ClickResult(
        content=_restore_code("".join(parts), stashed),
        max_clicks=max(current_click, highest_click),
        range_clicks=frozenset(range_clicks),
    )


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


def _resolve_click_defaults(deck_fm: dict, slide_fm: dict) -> ClickDefaults:
    def _get(key: str):
        return slide_fm.get(key, deck_fm.get(key))

    return ClickDefaults(
        animation=_get("click-animation") or "fade",
        duration=_get("click-duration"),
        delay=_get("click-delay"),
        ease=_get("click-ease"),
        spring=_get("click-spring"),
    )


def parse_deck(filepath: Path, *, use_motion: bool = False) -> Deck:
    raw_content = filepath.read_text()
    md = _create_markdown_renderer()
    raw_slides = split_slides(raw_content)

    first_fm, _ = parse_frontmatter(raw_slides[0]) if raw_slides else ({}, "")

    slides: list[SlideInfo] = []
    for idx, raw in enumerate(raw_slides):
        frontmatter, content = parse_frontmatter(raw)
        content, note = extract_notes(content)
        content = transform_regions(content)
        content = transform_clicks_wrapper(content)
        defaults = _resolve_click_defaults(first_fm, frontmatter)
        result = transform_click_tags(
            content, defaults=defaults, use_motion=use_motion,
        )

        slides.append(
            SlideInfo(
                content=md.render(result.content),
                index=idx,
                frontmatter=frontmatter,
                note=note,
                max_clicks=result.max_clicks,
                range_clicks=result.range_clicks,
            )
        )

    deck_fm = slides[0].frontmatter if slides else {}
    config_keys = ("title", "theme", "transition", "click-animation",
                   "click-duration", "click-delay", "click-ease", "click-spring")
    config_fields = {
        k.replace("-", "_"): deck_fm[k]
        for k in config_keys
        if deck_fm.get(k) is not None
    }
    return Deck(slides=slides, config=DeckConfig(**config_fields))


def deck_has_clicks(deck_path: Path) -> bool:
    """Quick scan for click-related tags without full parsing."""
    text = deck_path.read_text()
    return any(
        f"<{tag}>" in text or f"<{tag} " in text
        for tag in ("click", "after", "clicks")
    )


def build_click_signals(deck: Deck, clicks_signal) -> list:
    """Build computed visibility signals shared by server and export."""
    max_deck_clicks = max((s.max_clicks for s in deck.slides), default=0)
    sigs = [Signal(f"vis{i}", clicks_signal >= i) for i in range(1, max_deck_clicks + 1)]

    all_ranges: set[tuple[int, int]] = set()
    for s in deck.slides:
        all_ranges.update(s.range_clicks)

    sigs.extend(
        Signal(f"vis_{lo}_{hi}", (clicks_signal >= lo) & (clicks_signal < hi))
        for lo, hi in sorted(all_ranges)
    )
    return sigs
