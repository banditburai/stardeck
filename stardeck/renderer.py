"""Rendering utilities for StarDeck."""

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from starhtml import Div, NotStr

from stardeck.models import Deck, SlideInfo


def render_code_block(code: str, language: str = "") -> Div:
    """Render a code block with syntax highlighting.

    Uses Pygments for highlighting, wraps in StarHTML Div with code-block class.
    """
    # Get lexer for the language
    try:
        if language:
            lexer = get_lexer_by_name(language)
        else:
            lexer = guess_lexer(code)
    except Exception:
        # Fallback to plain text
        from pygments.lexers import TextLexer

        lexer = TextLexer()

    # Format with HTML
    formatter = HtmlFormatter(nowrap=True, cssclass="highlight")
    highlighted = highlight(code, lexer, formatter)

    return Div(
        NotStr(f"<pre><code>{highlighted}</code></pre>"),
        cls="code-block",
    )


def render_slide(slide: SlideInfo, deck: Deck) -> Div:
    """Render a slide with layout classes and styling.

    Wraps content in StarHTML Div with slide-{index} and layout-{layout} classes.
    Applies background if specified in frontmatter.
    Uses slide.transition if set, otherwise falls back to deck.config.transition.
    """
    # Determine transition: slide-specific or deck default
    transition = slide.frontmatter.get("transition") or deck.config.transition

    classes = [
        f"slide-{slide.index}",
        f"layout-{slide.layout}",
        f"transition-{transition}",
        "slide",
    ]

    # Build style for background
    style = ""
    if slide.background:
        bg = slide.background
        if bg.startswith("#") or bg.startswith("rgb"):
            # Color background
            style = f"background-color: {bg};"
        else:
            # Image background
            style = f"background-image: url('{bg}'); background-size: cover; background-position: center;"

    return Div(
        NotStr(slide.content),
        id=f"slide-{slide.index}",
        cls=" ".join(classes),
        style=style if style else None,
        **{"data-slide-index": slide.index},
    )
