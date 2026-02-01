"""StarDeck server application."""

from pathlib import Path

from starhtml import Button, Div, Script, Signal, Span, Style, star_app

from stardeck.parser import parse_deck
from stardeck.renderer import render_slide

DECK_STYLES = """
.stardeck-root {
    --slide-width: 960px;
    --slide-height: 540px;
    --aspect-ratio: 16/9;
}

.deck-container {
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #1a1a1a;
    overflow: hidden;
}

.slide-viewport {
    width: var(--slide-width);
    height: var(--slide-height);
    background: white;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    overflow: hidden;
    position: relative;
}

.slide {
    width: 100%;
    height: 100%;
    padding: 3rem;
    display: flex;
    flex-direction: column;
}

.slide-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.layout-cover {
    justify-content: center;
    align-items: center;
    text-align: center;
}

.layout-default {
    justify-content: flex-start;
}

.navigation-bar {
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
}

.nav-btn {
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
}

.nav-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
    border-color: white;
}

.nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

.slide-counter {
    font-variant-numeric: tabular-nums;
    min-width: 4rem;
    text-align: center;
}

/* Transitions */
.transition-fade {
    animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Code blocks */
.code-block {
    font-family: 'Fira Code', 'Consolas', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
}
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

    @rt("/")
    def home():
        return Div(
            (slide_index := Signal("slide_index", 0)),
            (total_slides := Signal("total_slides", deck.total)),
            # Main presentation container
            Div(
                # Slide viewport
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
                        data_attr_disabled=slide_index == 0,
                    ),
                    Span(
                        data_text=slide_index + 1 + " / " + total_slides,
                        cls="slide-counter",
                    ),
                    Button(
                        "→",
                        cls="nav-btn",
                        data_attr_disabled=slide_index == total_slides - 1,
                    ),
                    cls="navigation-bar",
                ),
                id="deck-container",
                cls="deck-container",
            ),
            cls="stardeck-root",
        )

    return app, rt, deck
