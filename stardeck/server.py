"""StarDeck server application."""

from pathlib import Path

from starhtml import (
    Button,
    Div,
    Script,
    Signal,
    Span,
    Style,
    elements,
    get,
    signals,
    sse,
    star_app,
)
from starhtml.datastar import evt

from stardeck.parser import parse_deck
from stardeck.renderer import render_slide
from stardeck.themes import get_theme_css


def create_app(deck_path: Path, *, debug: bool = False, theme: str = "default"):
    """Create a StarDeck application.

    Args:
        deck_path: Path to the markdown file.
        debug: Enable debug mode.
        theme: Theme name to use (default: "default").

    Returns:
        Tuple of (app, route_decorator, deck).
    """
    deck = parse_deck(deck_path)
    theme_css = get_theme_css(theme)

    app, rt = star_app(
        title=deck.config.title,
        hdrs=[
            Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
            Style(theme_css),
        ],
        live=debug,
    )

    @rt("/")
    def home():
        return Div(
            (slide_index := Signal("slide_index", 0)),
            (total_slides := Signal("total_slides", deck.total)),
            # URL hash navigation on load
            Script(f"""
                setTimeout(function() {{
                    var hash = window.location.hash;
                    if (hash && hash.length > 1) {{
                        var slideNum = parseInt(hash.substring(1), 10);
                        if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= {deck.total}) {{
                            var idx = slideNum - 1;
                            var params = encodeURIComponent(JSON.stringify({{slide_index: 0, total_slides: {deck.total}}}));
                            new EventSource('/api/slide/' + idx + '?datastar=' + params);
                        }}
                    }}
                }}, 100);
            """),
            # Slide viewport (full screen)
            Div(
                render_slide(deck.slides[0], deck),
                id="slide-content",
                cls="slide-viewport",
            ),
            # Navigation controls
            Div(
                Button(
                    "←",
                    cls="nav-btn",
                    data_on_click=get("/api/slide/prev"),
                    data_attr_disabled=slide_index == 0,
                ),
                Span(
                    data_text=slide_index + 1 + " / " + total_slides,
                    cls="slide-counter",
                ),
                Button(
                    "→",
                    cls="nav-btn",
                    data_on_click=get("/api/slide/next"),
                    data_attr_disabled=slide_index == total_slides - 1,
                ),
                cls="navigation-bar",
            ),
            # Keyboard navigation (window-level)
            Span(
                data_on_keydown=(
                    [
                        (evt.key == "ArrowRight") & get("/api/slide/next"),
                        (evt.key == " ") & get("/api/slide/next"),
                        (evt.key == "ArrowLeft") & get("/api/slide/prev"),
                    ],
                    {"window": True},
                ),
                style="display: none",
            ),
            cls="stardeck-root",
        )

    @rt("/api/slide/next")
    @sse
    def next_slide(slide_index: int = 0):
        new_idx = min(slide_index + 1, deck.total - 1)
        yield signals(slide_index=new_idx)
        yield elements(render_slide(deck.slides[new_idx], deck), "#slide-content", "inner")

    @rt("/api/slide/prev")
    @sse
    def prev_slide(slide_index: int = 0):
        new_idx = max(slide_index - 1, 0)
        yield signals(slide_index=new_idx)
        yield elements(render_slide(deck.slides[new_idx], deck), "#slide-content", "inner")

    @rt("/api/slide/{idx}")
    @sse
    def goto_slide(idx: int):
        idx = max(0, min(idx, deck.total - 1))
        yield signals(slide_index=idx)
        yield elements(render_slide(deck.slides[idx], deck), "#slide-content", "inner")

    return app, rt, deck
