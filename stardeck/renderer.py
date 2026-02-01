"""Rendering utilities for StarDeck."""

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from starhtml import Div, NotStr


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
