"""StarDeck server application."""

import time
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
from starlette.responses import JSONResponse

from stardeck.parser import parse_deck
from stardeck.renderer import render_slide
from stardeck.themes import get_theme_css


def create_app(deck_path: Path, *, debug: bool = False, theme: str = "default", watch: bool = False):
    """Create a StarDeck application.

    Args:
        deck_path: Path to the markdown file.
        debug: Enable debug mode.
        theme: Theme name to use (default: "default").
        watch: Enable watch mode for hot reload on file changes.

    Returns:
        Tuple of (app, route_decorator, deck_state).
    """
    # Use mutable container so deck can be re-parsed on reload
    # reload_timestamp is used by watch mode to detect file changes
    deck_state = {
        "deck": parse_deck(deck_path),
        "path": deck_path,
        "watch": watch,
        "reload_timestamp": int(time.time() * 1000),
    }
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
        initial_slide = deck.slides[0]
        return Div(
            (slide_index := Signal("slide_index", 0)),
            (total_slides := Signal("total_slides", deck.total)),
            (clicks := Signal("clicks", 0)),
            (max_clicks := Signal("max_clicks", initial_slide.max_clicks)),
            # URL hash navigation on load - uses Datastar's data-init
            Span(
                data_init="""
                    const hash = window.location.hash;
                    if (hash && hash.length > 1) {
                        const slideNum = parseInt(hash.substring(1), 10);
                        if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                            @get('/api/slide/' + (slideNum - 1))
                        }
                    }
                """,
                style="display: none",
            ),
            # URL hash change listener - handles manual URL changes and back/forward
            Span(
                data_on_hashchange=(
                    """
                    const hash = window.location.hash;
                    if (hash && hash.length > 1) {
                        const slideNum = parseInt(hash.substring(1), 10);
                        if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                            @get('/api/slide/' + (slideNum - 1))
                        }
                    }
                    """,
                    {"window": True},
                ),
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
            # Keyboard navigation with click support (window-level)
            Span(
                data_on_keydown=(
                    """
                    if (evt.key === 'ArrowRight' || evt.key === ' ') {
                        evt.preventDefault();
                        if ($clicks < $max_clicks) {
                            $clicks++;
                        } else {
                            $clicks = 0;
                            @get('/api/slide/next');
                        }
                    } else if (evt.key === 'ArrowLeft') {
                        evt.preventDefault();
                        if ($clicks > 0) {
                            $clicks--;
                        } else {
                            @get('/api/slide/prev');
                        }
                    }
                    """,
                    {"window": True},
                ),
                style="display: none",
            ),
            # URL hash update on navigation - uses Datastar effect (DS-005)
            Span(
                data_effect="window.history.replaceState(null, '', '#' + ($slide_index + 1))",
                style="display: none",
            ),
            # Watch mode polling for hot reload (only when watch=True)
            Span(
                (_watch_ts := Signal("_watch_ts", deck_state["reload_timestamp"])),
                data_on_interval=(
                    """
                    fetch('/api/watch-status')
                        .then(r => r.json())
                        .then(data => {
                            if (data.timestamp > $_watch_ts) {
                                $_watch_ts = data.timestamp;
                                @get('/api/reload')
                            }
                        })
                    """,
                    {"duration": "1s"},
                ),
                style="display: none",
            ) if deck_state.get("watch") else None,
            cls="stardeck-root",
        )

    @rt("/api/slide/next")
    @sse
    def next_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        new_idx = min(slide_index + 1, current_deck.total - 1)
        new_slide = current_deck.slides[new_idx]
        yield signals(slide_index=new_idx, clicks=0, max_clicks=new_slide.max_clicks)
        yield elements(render_slide(new_slide, current_deck), "#slide-content", "inner")

    @rt("/api/slide/prev")
    @sse
    def prev_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        new_idx = max(slide_index - 1, 0)
        new_slide = current_deck.slides[new_idx]
        yield signals(slide_index=new_idx, clicks=0, max_clicks=new_slide.max_clicks)
        yield elements(render_slide(new_slide, current_deck), "#slide-content", "inner")

    @rt("/api/slide/{idx}")
    @sse
    def goto_slide(idx: int):
        current_deck = deck_state["deck"]
        idx = max(0, min(idx, current_deck.total - 1))
        new_slide = current_deck.slides[idx]
        yield signals(slide_index=idx, clicks=0, max_clicks=new_slide.max_clicks)
        yield elements(render_slide(new_slide, current_deck), "#slide-content", "inner")

    @rt("/api/reload")
    @sse
    def reload_deck(slide_index: int = 0):
        """Re-parse deck and re-render current slide after file change."""
        deck_state["deck"] = parse_deck(deck_state["path"])
        current_deck = deck_state["deck"]
        idx = min(slide_index, current_deck.total - 1)
        new_slide = current_deck.slides[idx]
        yield signals(slide_index=idx, total_slides=current_deck.total, clicks=0, max_clicks=new_slide.max_clicks)
        yield elements(render_slide(new_slide, current_deck), "#slide-content", "inner")

    @rt("/api/watch-status")
    def watch_status():
        """Return current reload timestamp for watch mode polling."""
        return JSONResponse({"timestamp": deck_state.get("reload_timestamp", 0)})

    return app, rt, deck_state
