"""Rendering utilities for StarDeck."""

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from starhtml import Code, Div, NotStr, Pre

from stardeck.models import Deck, SlideInfo


def _resolve_asset_url(raw: str) -> str:
    if raw.startswith(("http://", "https://", "/", "data:")):
        return raw
    if raw.startswith("./"):
        return raw[1:]
    return f"/{raw}"


def render_code_block(code: str, language: str = "") -> Div:
    """Render a code block with syntax highlighting."""
    try:
        lexer = get_lexer_by_name(language) if language else guess_lexer(code)
    except Exception:
        from pygments.lexers import TextLexer

        lexer = TextLexer()

    formatter = HtmlFormatter(nowrap=True, cssclass="highlight")
    highlighted = highlight(code, lexer, formatter)

    return Div(
        Pre(Code(NotStr(highlighted))),
        cls="code-block",
    )


def render_slide(slide: SlideInfo, deck: Deck) -> Div:
    """Render a slide as a styled Div."""
    transition = slide.frontmatter.get("transition") or deck.config.transition

    classes = [
        f"slide-{slide.index}",
        f"layout-{slide.layout}",
        f"transition-{transition}",
        "slide",
    ]

    user_classes = slide.frontmatter.get("class") or slide.frontmatter.get("cls") or ""
    if user_classes:
        classes.extend(user_classes.split())

    style = ""
    if slide.background:
        bg = slide.background
        if bg.startswith(("#", "rgb")):
            style = f"background-color: {bg};"
        else:
            url = _resolve_asset_url(bg)
            style = f"background-image: url('{url}'); background-size: cover; background-position: center;"

    cols = slide.frontmatter.get("cols")
    if cols and slide.layout == "grid":
        style += f" --grid-cols: {int(cols)};"

    image_layouts = {"image-left", "image-right", "hero", "caption"}
    image_url = slide.frontmatter.get("image", "")

    if slide.layout in image_layouts and image_url:
        url = _resolve_asset_url(image_url)
        content = (
            f'<div class="slot-image" style="background-image: url(\'{url}\'); '
            f'background-size: cover; background-position: center;"></div>'
            f'<div class="slot-content">{slide.content}</div>'
        )
    else:
        content = slide.content

    return Div(
        NotStr(content),
        id=f"slide-{slide.index}",
        cls=" ".join(classes),
        style=style if style else None,
        data_slide_index=slide.index,
    )
