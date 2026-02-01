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
        Tuple of (app, route_decorator, deck_state).
    """
    # Use mutable container so deck can be re-parsed on reload
    deck_state = {"deck": parse_deck(deck_path), "path": deck_path}
    theme_css = get_theme_css(theme)

    deck = deck_state["deck"]  # Initial deck reference

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
            (_hash_checked := Signal("_hash_checked", False)),  # Local signal (DS-006)
            # URL hash navigation on load - uses Datastar's load event and @get action
            Span(
                data_on_load="""
                    if (!$_hash_checked) {
                        $_hash_checked = true;
                        const hash = window.location.hash;
                        if (hash && hash.length > 1) {
                            const slideNum = parseInt(hash.substring(1), 10);
                            if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                                @get('/api/slide/' + (slideNum - 1));
                            }
                        }
                    }
                """,
                style="display: none",
            ),
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
            # URL hash update on navigation - uses Datastar effect (DS-005)
            Span(
                data_effect="window.history.replaceState(null, '', '#' + ($slide_index + 1))",
                style="display: none",
            ),
            cls="stardeck-root",
        )

    @rt("/api/slide/next")
    @sse
    def next_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        new_idx = min(slide_index + 1, current_deck.total - 1)
        yield signals(slide_index=new_idx)
        yield elements(render_slide(current_deck.slides[new_idx], current_deck), "#slide-content", "inner")

    @rt("/api/slide/prev")
    @sse
    def prev_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        new_idx = max(slide_index - 1, 0)
        yield signals(slide_index=new_idx)
        yield elements(render_slide(current_deck.slides[new_idx], current_deck), "#slide-content", "inner")

    @rt("/api/slide/{idx}")
    @sse
    def goto_slide(idx: int):
        current_deck = deck_state["deck"]
        idx = max(0, min(idx, current_deck.total - 1))
        yield signals(slide_index=idx)
        yield elements(render_slide(current_deck.slides[idx], current_deck), "#slide-content", "inner")

    @rt("/api/reload")
    @sse
    def reload_deck(slide_index: int = 0):
        """Re-parse deck and re-render current slide after file change."""
        deck_state["deck"] = parse_deck(deck_state["path"])
        current_deck = deck_state["deck"]
        idx = min(slide_index, current_deck.total - 1)
        yield signals(slide_index=idx, total_slides=current_deck.total)
        yield elements(render_slide(current_deck.slides[idx], current_deck), "#slide-content", "inner")

    return app, rt, deck_state
