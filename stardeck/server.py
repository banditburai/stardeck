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
from starhtml.plugins import resize

from stardeck.parser import parse_deck
from stardeck.renderer import render_slide

# Slide dimensions (16:9 aspect ratio)
SLIDE_WIDTH = 960
SLIDE_HEIGHT = 540
NAV_BAR_HEIGHT = 100
SCALE_FACTOR = 0.85

DECK_STYLES = f"""
.stardeck-root {{
    --slide-width: {SLIDE_WIDTH}px;
    --slide-height: {SLIDE_HEIGHT}px;
    --aspect-ratio: 16/9;
}}

.deck-container {{
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #1a1a1a;
    overflow: hidden;
}}

.slide-viewport {{
    width: var(--slide-width);
    height: var(--slide-height);
    background: white;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    overflow: hidden;
    position: relative;
    transform-origin: center center;
    transition: transform 0.1s ease-out;
}}

.slide {{
    width: 100%;
    height: 100%;
    padding: 3rem;
    display: flex;
    flex-direction: column;
}}

.slide-content {{
    flex: 1;
    display: flex;
    flex-direction: column;
}}

.layout-cover {{
    justify-content: center;
    align-items: center;
    text-align: center;
}}

.layout-default {{
    justify-content: flex-start;
}}

.navigation-bar {{
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    background: rgba(0, 0, 0, 0.8);
    border-radius: 0.5rem;
    color: white;
}}

.nav-btn {{
    width: 2.5rem;
    height: 2.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 0.25rem;
    color: white;
    cursor: pointer;
    transition: all 0.2s;
}}

.nav-btn:hover:not(:disabled) {{
    background: rgba(255, 255, 255, 0.1);
    border-color: white;
}}

.nav-btn:disabled {{
    opacity: 0.3;
    cursor: not-allowed;
}}

.slide-counter {{
    font-variant-numeric: tabular-nums;
    min-width: 4rem;
    text-align: center;
}}

/* Transitions */
.transition-fade {{
    animation: fadeIn 0.3s ease-out;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to {{ opacity: 1; }}
}}

/* Code blocks */
.code-block {{
    font-family: 'Fira Code', 'Consolas', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
}}
"""


def create_app(deck_path: Path, *, debug: bool = False):
    """Create a StarDeck application.

    Args:
        deck_path: Path to the markdown file.
        debug: Enable debug mode.

    Returns:
        Tuple of (app, route_decorator, deck).
    """
    deck = parse_deck(deck_path)

    app, rt = star_app(
        title=deck.config.title,
        hdrs=[
            Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
            Style(DECK_STYLES),
        ],
        live=debug,
    )
    app.register(resize)

    @rt("/")
    def home():
        return Div(
            (slide_index := Signal("slide_index", 0)),
            (total_slides := Signal("total_slides", deck.total)),
            (scale := Signal("scale", 1.0)),
            # Main presentation container
            Div(
                # Slide viewport with dynamic scaling
                Div(
                    render_slide(deck.slides[0], deck),
                    id="slide-content",
                    cls="slide-viewport",
                    data_style="{transform: `scale(${" + scale.to_js() + "})`}",
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
                id="deck-container",
                cls="deck-container",
                # Calculate scale on resize to fit slide in viewport
                data_resize=f"$scale = Math.min($resize_window_width / {SLIDE_WIDTH}, ($resize_window_height - {NAV_BAR_HEIGHT}) / {SLIDE_HEIGHT}) * {SCALE_FACTOR}",
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
