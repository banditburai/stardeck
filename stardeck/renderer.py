"""Rendering utilities for StarDeck."""

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from starhtml import Code, Div, NotStr, Pre

from stardeck.models import Deck, SlideInfo


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

    style = ""
    if slide.background:
        bg = slide.background
        if bg.startswith(("#", "rgb")):
            style = f"background-color: {bg};"
        else:
            if bg.startswith(("http://", "https://", "/", "data:")):
                url = bg
            elif bg.startswith("./"):
                url = bg[1:]  # "./assets/foo.jpg" -> "/assets/foo.jpg"
            else:
                url = f"/{bg}"  # "assets/foo.jpg" -> "/assets/foo.jpg"
            style = f"background-image: url('{url}'); background-size: cover; background-position: center;"

    return Div(
        NotStr(slide.content),
        id=f"slide-{slide.index}",
        cls=" ".join(classes),
        style=style if style else None,
        data_slide_index=slide.index,
    )
